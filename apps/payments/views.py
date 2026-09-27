"""
Checkout endpoints.

Flow (both gateways):
  1. POST /api/v1/payments/initiate/ (or cart-checkout/) -> pending rows + gateway order
  2a. PhonePe:  browser -> redirect_url -> PhonePe -> /api/v1/payments/callback/
  2b. Razorpay: browser opens checkout.js -> POST /api/v1/payments/razorpay/confirm/
  3. Webhooks (both) are the server-side backstop.
All paths fulfil through apps.payments.services.complete_order (idempotent).
"""

import json
import logging
import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.albums.models import AlbumPack
from apps.commerce.models import Purchase
from apps.core.net import get_client_ip  # noqa: F401  (re-exported for older imports)
from apps.tracks.models import Track

from .services import complete_order, fail_order
from .utils import SUPPORTED_GATEWAYS, get_gateway  # noqa: F401

logger = logging.getLogger("mixmint")

CONTENT_TYPES = ("track", "album")


def get_device_hash(request):
    import hashlib

    ua = request.META.get("HTTP_USER_AGENT", "unknown")
    accept = request.META.get("HTTP_ACCEPT", "")
    lang = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
    return hashlib.sha256(f"{ua}|{accept}|{lang}".encode()).hexdigest()


def run_fraud_checks(user_id, data):
    from apps.admin_panel.middleware import FraudDetector

    return FraudDetector.check_purchase(user_id, data)


def _buyer_fee():
    from apps.admin_panel.models import PlatformSettings

    s = PlatformSettings.load()
    return Decimal(s.buyer_platform_fee) if s.buyer_platform_fee_enabled else Decimal("0.00")


def calculate_total_price_paise(content, is_redownload=False):
    price = Decimal(content.price)
    if is_redownload:
        price = (price * Decimal("0.5")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(((price + _buyer_fee()) * 100).to_integral_value(rounding=ROUND_HALF_UP))


def normalize_content_type(content_type):
    return "album" if content_type in ("album", "zip") else content_type


def get_content_object(content_id, content_type):
    content_type = normalize_content_type(content_type)
    if content_type == "track":
        return Track.objects.select_related("dj__profile").get(id=content_id, is_active=True, is_deleted=False)
    if content_type == "album":
        return AlbumPack.objects.select_related("dj__profile").get(id=content_id, is_active=True, is_deleted=False)
    raise ValueError("Invalid content type.")


def _gateway_payload(result, order_id, amount_paise):
    """What the browser needs to continue: a redirect (PhonePe) or checkout.js params (Razorpay)."""
    if result.get("redirect_url"):
        return {"checkout": "redirect", "redirect_url": result["redirect_url"], "order_id": order_id}
    return {
        "checkout": "razorpay",
        "order_id": result["gateway_order_id"],
        "key": result.get("key"),
        "amount": amount_paise,
        "currency": result.get("currency", "INR"),
        "confirm_url": "/api/v1/payments/razorpay/confirm/",
        "name": "MixMint",
    }


def _create_gateway_order(gateway, amount_paise, internal_id, metadata):
    result = gateway.create_order(amount_paise=amount_paise, order_id=internal_id, metadata=metadata)
    return result, result.get("gateway_order_id") or result.get("order_id") or internal_id


def _json_body(request):
    try:
        data = json.loads(request.body or b"{}")
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _gateway_error(exc):
    logger.exception("Payment gateway error")
    msg = "Payment gateway is unavailable right now. Please try again in a minute."
    if settings.DEBUG:
        msg += f" ({exc})"
    return JsonResponse({"error": msg}, status=502)


@login_required
@require_POST
def initiate_purchase(request):
    """Buyer clicks "Buy" -> pending Purchase + gateway order. Price is always computed server-side."""
    data = _json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    content_type = data.get("content_type")
    if content_type == "dj_application":
        return _initiate_dj_application_fee(request, data)

    content_type = normalize_content_type(content_type)
    content_id = data.get("content_id")
    is_redownload = bool(data.get("is_redownload", False))
    profile = request.user.profile

    if content_type not in CONTENT_TYPES:
        return JsonResponse({"error": "Invalid content type."}, status=400)
    try:
        content_id = int(content_id)
        content_obj = get_content_object(content_id, content_type)
    except (TypeError, ValueError, Track.DoesNotExist, AlbumPack.DoesNotExist):
        return JsonResponse({"error": "Content not found."}, status=404)

    if content_obj.dj.profile.store_paused:
        return JsonResponse({"error": "This store is temporarily paused."}, status=400)
    if getattr(profile, "dj_profile", None) is not None and profile.dj_profile == content_obj.dj:
        return JsonResponse({"error": "You cannot purchase your own content.", "self_purchase": True}, status=400)
    if content_obj.price <= 0:
        return JsonResponse({"error": "This item is free — use the download button.", "free": True}, status=400)

    owned = Purchase.objects.filter(
        user=profile, content_type=content_type, content_id=content_id, status="paid", is_revoked=False
    )
    if is_redownload:
        # Re-download at 50% is only for owners whose lock has expired [Spec §4.3].
        from apps.downloads.utils import DownloadManager

        if not owned.filter(is_redownload=False).exists():
            return JsonResponse({"error": "You need to own this item before buying a re-download."}, status=400)
        eligible, msg = DownloadManager.check_redownload_eligibility(profile, content_id, content_type)
        if not eligible or not owned.filter(download_completed=True).exists():
            return JsonResponse({"error": msg or "Re-download is not needed right now."}, status=400)
    elif owned.filter(is_redownload=False).exists():
        return JsonResponse({"error": f"You already own this {content_type}.", "already_owned": True}, status=400)

    fraud_ok, _risk, _flags = run_fraud_checks(
        request.user.id,
        {"ip_address": get_client_ip(request), "device_hash": get_device_hash(request), "content_id": content_id},
    )
    if not fraud_ok:
        return JsonResponse({"error": "Purchase could not be processed. Please try again later."}, status=403)

    fee = _buyer_fee()
    amount_paise = calculate_total_price_paise(content_obj, is_redownload)
    internal_id = f"MM_{uuid.uuid4().hex[:16].upper()}"

    try:
        gateway = get_gateway(data.get("gateway"))
    except Exception as exc:
        return _gateway_error(exc)

    with transaction.atomic():
        purchase = Purchase.objects.create(
            user=profile,
            content_type=content_type,
            content_id=content_id,
            seller=content_obj.dj,
            gateway_order_id=internal_id,
            payment_gateway=gateway.name,
            amount_paise=amount_paise,
            original_price=content_obj.price,
            price_paid=Decimal(amount_paise) / 100,
            platform_fee=fee,
            checkout_fee=fee,
            is_redownload=is_redownload,
            buyer_role=profile.role,
            status="pending",
        )
        try:
            result, gateway_order_id = _create_gateway_order(
                gateway,
                amount_paise,
                internal_id,
                {"user_id": str(request.user.id), "purchase_id": str(purchase.id)},
            )
        except Exception as exc:
            transaction.set_rollback(True)
            return _gateway_error(exc)
        if gateway_order_id != internal_id:
            purchase.gateway_order_id = gateway_order_id
            purchase.save(update_fields=["gateway_order_id"])

    payload = _gateway_payload(result, gateway_order_id, amount_paise)
    payload["description"] = content_obj.title
    payload["prefill"] = {"email": request.user.email, "name": profile.full_name}
    return JsonResponse(payload)


def _initiate_dj_application_fee(request, data):
    from apps.commerce.models import DJApplicationFee

    profile = request.user.profile
    dj = getattr(profile, "dj_profile", None)
    if dj is None or dj.status != "pending_payment":
        return JsonResponse({"error": "No application fee is due."}, status=400)
    fee, _ = DJApplicationFee.objects.get_or_create(dj=dj, defaults={"amount": Decimal("99.00")})
    if fee.status == "paid":
        return JsonResponse({"error": "Application fee already paid."}, status=400)
    amount_paise = int(Decimal(fee.amount) * 100)
    internal_id = f"DJAPP_{uuid.uuid4().hex[:14].upper()}"
    try:
        gateway = get_gateway(data.get("gateway"))
        result, gateway_order_id = _create_gateway_order(
            gateway, amount_paise, internal_id, {"user_id": str(request.user.id), "purpose": "dj_application"}
        )
    except Exception as exc:
        return _gateway_error(exc)
    fee.payment_id = gateway_order_id
    fee.status = "pending"
    fee.save(update_fields=["payment_id", "status"])
    payload = _gateway_payload(result, gateway_order_id, amount_paise)
    payload["description"] = "DJ Partner Application Fee"
    return JsonResponse(payload)


def _fulfil_from_status(order_id, gateway_name):
    """Ask the gateway for the truth and act on it. Returns 'success' | 'failed' | 'pending'."""
    gateway = get_gateway(gateway_name)
    status_data = gateway.get_payment_status(order_id)
    if status_data.get("success") and status_data.get("status") == "PAYMENT_SUCCESS":
        result = complete_order(
            order_id,
            gateway_payment_id=status_data.get("transaction_id", ""),
            gateway_response=status_data.get("gateway_response"),
            paid_amount_paise=status_data.get("amount"),
        )
        return "success" if result in ("ok", "already_processed") else "failed"
    if status_data.get("status") in ("PAYMENT_DECLINED", "PAYMENT_ERROR", "TIMED_OUT"):
        fail_order(order_id, status_data.get("gateway_response"))
        return "failed"
    return "pending"


def _gateway_for_order(order_id):
    first = Purchase.objects.filter(gateway_order_id=order_id).first()
    if first:
        return first.payment_gateway
    return "razorpay" if str(order_id).startswith("order_") else "phonepe"


@csrf_exempt  # read-only: only asks the gateway for the order's real status
def payment_callback(request):
    """Buyer lands here after the PhonePe page. The gateway's status API is the source of truth."""
    order_id = request.GET.get("order_id") or request.POST.get("transactionId") or ""
    if not order_id:
        return HttpResponseRedirect("/library/?payment=failed")
    try:
        outcome = _fulfil_from_status(order_id, _gateway_for_order(order_id))
    except Exception:
        logger.exception("Payment status lookup failed for %s", order_id)
        outcome = "pending"
    target = "/dashboard/" if order_id.startswith(("DJAPP_", "PRO_")) else "/library/"
    return HttpResponseRedirect(f"{target}?order_id={order_id}&payment={outcome}")


@login_required
@require_POST
def razorpay_confirm(request):
    """checkout.js success handler posts here. Signature proves the payment belongs to this order."""
    data = _json_body(request) or {}
    order_id = data.get("razorpay_order_id") or data.get("order_id")
    payment_id = data.get("razorpay_payment_id") or data.get("payment_id")
    signature = data.get("razorpay_signature") or data.get("signature")
    if not (order_id and payment_id and signature):
        return JsonResponse({"error": "Missing payment details."}, status=400)

    try:
        gateway = get_gateway("razorpay")
    except Exception as exc:
        return _gateway_error(exc)
    if not gateway.verify_payment({"order_id": order_id, "payment_id": payment_id}, signature):
        return JsonResponse({"error": "Payment verification failed."}, status=400)

    # Order must belong to the logged-in buyer (or be their own fee/subscription/insurance).
    owns = Purchase.objects.filter(gateway_order_id=order_id, user=request.user.profile).exists()
    if not owns:
        from apps.commerce.models import DJApplicationFee, ProSubscriptionEvent
        from apps.downloads.models import DownloadInsurance

        owns = (
            DownloadInsurance.objects.filter(payment_id=order_id, user=request.user.profile).exists()
            or DJApplicationFee.objects.filter(payment_id=order_id, dj__profile=request.user.profile).exists()
            or ProSubscriptionEvent.objects.filter(gateway_order_id=order_id, dj__profile=request.user.profile).exists()
        )
    if not owns:
        return JsonResponse({"error": "Order not found."}, status=404)

    try:
        payment = gateway.fetch_payment(payment_id)
    except Exception as exc:
        return _gateway_error(exc)
    if payment.get("order_id") != order_id:
        return JsonResponse({"error": "Payment does not match this order."}, status=400)
    if payment.get("status") == "authorized":
        try:
            gateway.client.payment.capture(payment_id, payment["amount"], {"currency": payment.get("currency", "INR")})
            payment["status"] = "captured"
        except Exception:
            logger.exception("Razorpay capture failed for %s", payment_id)
    if payment.get("status") != "captured":
        return JsonResponse({"status": "pending", "message": "Payment is processing. Check your library shortly."})

    result = complete_order(
        order_id, gateway_payment_id=payment_id, gateway_response=payment, paid_amount_paise=payment.get("amount")
    )
    if result in ("ok", "already_processed"):
        return JsonResponse({"status": "success", "redirect_url": f"/library/?order_id={order_id}&payment=success"})
    return JsonResponse({"error": "Payment could not be matched to your order. Support has been notified."}, status=409)


@login_required
def cart_page(request):
    return render(request, "commerce/cart.html")


@login_required
@require_POST
def cart_checkout(request):
    """Checkout every cart item as one gateway order with tiered bundle discount (all amounts in paise)."""
    from apps.commerce.models import Cart

    data = _json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    profile = request.user.profile

    try:
        cart = Cart.objects.get(id=data.get("cart_id"), user=profile, is_active=True)
    except (Cart.DoesNotExist, ValueError, Exception):
        return JsonResponse({"error": "Cart not found."}, status=404)

    items = list(cart.items.all())
    if not items:
        return JsonResponse({"error": "Cart is empty."}, status=400)

    # Re-price from the catalogue (cart prices can be stale) and re-validate every item.
    lines = []
    for item in items:
        try:
            content = get_content_object(item.content_id, item.content_type)
        except Exception:
            return JsonResponse({"error": "An item in your cart is no longer available. Please remove it."}, status=400)
        if Purchase.objects.filter(
            user=profile,
            content_type=item.content_type,
            content_id=item.content_id,
            status="paid",
            is_revoked=False,
            is_redownload=False,
        ).exists():
            return JsonResponse({"error": f"You already own “{content.title}”. Remove it from your cart."}, status=400)
        if getattr(profile, "dj_profile", None) is not None and profile.dj_profile == content.dj:
            return JsonResponse({"error": "You cannot purchase your own content."}, status=400)
        if content.price <= 0 or content.dj.profile.store_paused:
            return JsonResponse({"error": f"“{content.title}” can't be bought right now. Remove it."}, status=400)
        lines.append((item, content, int((Decimal(content.price) * 100).to_integral_value())))

    fraud_ok, _risk, _flags = run_fraud_checks(
        request.user.id, {"ip_address": get_client_ip(request), "device_hash": get_device_hash(request)}
    )
    if not fraud_ok:
        return JsonResponse({"error": "Purchase could not be processed. Please try again later."}, status=403)

    discount_pct = cart.discount_percentage
    subtotal = sum(p for _, _, p in lines)
    discount = (subtotal * discount_pct + 50) // 100
    fee_paise = int(_buyer_fee() * 100)
    total_paise = subtotal - discount + fee_paise
    if total_paise <= 0:
        return JsonResponse({"error": "Cart total is too low for processing."}, status=400)

    # Spread the discount over lines (largest-remainder) so per-item amounts sum exactly to the charge.
    shares = []
    remaining_discount = discount
    for idx, (item, content, price) in enumerate(lines):
        d = remaining_discount if idx == len(lines) - 1 else (price * discount) // subtotal
        remaining_discount -= d
        shares.append(price - d)
    shares[0] += fee_paise  # the one buyer fee rides on the first line

    internal_id = f"MMC_{uuid.uuid4().hex[:14].upper()}"
    try:
        gateway = get_gateway(data.get("gateway"))
    except Exception as exc:
        return _gateway_error(exc)

    with transaction.atomic():
        created = []
        for idx, ((item, content, price), amount) in enumerate(zip(lines, shares)):
            created.append(
                Purchase.objects.create(
                    user=profile,
                    content_type=item.content_type,
                    content_id=item.content_id,
                    seller=content.dj,
                    gateway_order_id=internal_id,
                    payment_gateway=gateway.name,
                    amount_paise=amount,
                    original_price=content.price,
                    price_paid=Decimal(amount) / 100,
                    platform_fee=Decimal(fee_paise) / 100 if idx == 0 else Decimal("0.00"),
                    checkout_fee=Decimal(fee_paise) / 100 if idx == 0 else Decimal("0.00"),
                    cart_id=cart.id,
                    discount_applied=discount_pct,
                    final_price=amount,
                    buyer_role=profile.role,
                    status="pending",
                )
            )
        try:
            result, gateway_order_id = _create_gateway_order(
                gateway,
                total_paise,
                internal_id,
                {"user_id": str(request.user.id), "cart_id": str(cart.id)},
            )
        except Exception as exc:
            transaction.set_rollback(True)
            return _gateway_error(exc)
        if gateway_order_id != internal_id:
            Purchase.objects.filter(gateway_order_id=internal_id).update(gateway_order_id=gateway_order_id)
        # The cart stays intact until payment succeeds (paid items are removed then),
        # so a cancelled or failed payment never loses the buyer's cart.

    payload = _gateway_payload(result, gateway_order_id, total_paise)
    payload["description"] = f"{len(lines)} item(s)"
    payload["prefill"] = {"email": request.user.email, "name": profile.full_name}
    return JsonResponse(payload)
