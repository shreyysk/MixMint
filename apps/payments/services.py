"""
Single completion path for every gateway order.

Callback page, PhonePe webhook, Razorpay webhook and Razorpay checkout confirm
all call `complete_order` / `fail_order`. Rows are locked, the amount is checked
against what we charged, and each order kind is fulfilled exactly once.

Order kinds (looked up by gateway order id):
    Purchase rows          -> track/album/cart sales
    DownloadInsurance      -> payment_id holds the order id while status="pending"
    DJApplicationFee       -> payment_id holds the order id while status="pending"
    ProSubscriptionEvent   -> event_type="payment_initiated"
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("mixmint")

OK = "ok"
NOT_FOUND = "not_found"
AMOUNT_MISMATCH = "amount_mismatch"
ALREADY = "already_processed"


def _paise(value):
    return int((Decimal(value or 0) * 100).to_integral_value())


def _amount_ok(expected_paise, paid_amount_paise, order_id):
    if paid_amount_paise is None:
        return True
    try:
        if int(paid_amount_paise) == int(expected_paise):
            return True
    except (TypeError, ValueError):
        pass
    logger.error(
        "Order %s amount mismatch: paid=%r expected=%s. NOT fulfilling.", order_id, paid_amount_paise, expected_paise
    )
    return False


def complete_order(order_id, gateway_payment_id="", gateway_response=None, paid_amount_paise=None):
    """Fulfil an order that the gateway reports as paid. Idempotent."""
    if not order_id:
        return NOT_FOUND
    from apps.commerce.models import Purchase

    if Purchase.objects.filter(gateway_order_id=order_id).exists():
        return _complete_purchases(order_id, gateway_payment_id, gateway_response, paid_amount_paise)
    for handler in (_complete_insurance, _complete_dj_application, _complete_pro_subscription):
        result = handler(order_id, gateway_payment_id, gateway_response, paid_amount_paise)
        if result != NOT_FOUND:
            return result
    logger.warning("complete_order: no order found for %s", order_id)
    return NOT_FOUND


def fail_order(order_id, gateway_response=None):
    """Mark still-pending purchases of an order as failed (never touches paid rows)."""
    from apps.commerce.models import Purchase

    return Purchase.objects.filter(gateway_order_id=order_id, status="pending").update(
        status="failed", gateway_response=gateway_response
    )


def _complete_purchases(order_id, gateway_payment_id, gateway_response, paid_amount_paise):
    from apps.commerce.models import Purchase
    from apps.commerce.services import MonetizationService

    newly_paid = []
    with transaction.atomic():
        purchases = list(Purchase.objects.select_for_update().filter(gateway_order_id=order_id).order_by("pk"))
        expected = sum(p.amount_paise if p.amount_paise is not None else _paise(p.price_paid) for p in purchases)
        if not _amount_ok(expected, paid_amount_paise, order_id):
            return AMOUNT_MISMATCH

        for p in purchases:
            if p.status in ("paid", "refunded", "disputed"):
                continue
            p.status = "paid"
            p.gateway_payment_id = gateway_payment_id or p.gateway_payment_id
            p.gateway_response = gateway_response
            p.paid_at = timezone.now()
            p.is_completed = True
            p.save()
            newly_paid.append(p)

        for p in newly_paid:
            MonetizationService.complete_purchase(p)
            if p.cart_id:
                from apps.commerce.models import CartItem

                CartItem.objects.filter(
                    cart_id=p.cart_id, content_type=p.content_type, content_id=p.content_id
                ).delete()
            if p.is_redownload:
                # A paid re-download re-opens the download for the buyer (fresh attempts too).
                from apps.downloads.models import DownloadAttempt

                Purchase.objects.filter(
                    user=p.user, content_type=p.content_type, content_id=p.content_id, status="paid"
                ).update(download_completed=False)
                DownloadAttempt.objects.filter(
                    user=p.user, content_type=p.content_type, content_id=p.content_id
                ).delete()

    for p in newly_paid:
        transaction.on_commit(lambda p=p: _notify_sale(p))
    return OK if newly_paid else ALREADY


def _notify_sale(purchase):
    try:
        from apps.core.push_notifications import PushNotificationService

        obj = purchase.get_content_object
        title = getattr(obj, "title", None) or f"{purchase.content_type} #{purchase.content_id}"
        PushNotificationService.notify_sale(dj_profile=purchase.seller, track_title=title, amount=purchase.dj_revenue)
    except Exception:
        logger.exception("Sale notification failed for purchase %s", purchase.id)
    try:
        from apps.core.email_service import EmailService

        EmailService.send_purchase_confirmation(purchase)
    except Exception:
        logger.debug("Purchase confirmation email skipped for %s", purchase.id, exc_info=True)


def _complete_insurance(order_id, gateway_payment_id, gateway_response, paid_amount_paise):
    from apps.downloads.models import DownloadInsurance

    with transaction.atomic():
        ins = DownloadInsurance.objects.select_for_update().filter(payment_id=order_id).first()
        if not ins:
            return NOT_FOUND
        if ins.status != "pending":
            return ALREADY
        if not _amount_ok(_paise(ins.insurance_price), paid_amount_paise, order_id):
            return AMOUNT_MISMATCH
        ins.status = "active"
        ins.payment_id = gateway_payment_id or order_id
        ins.save(update_fields=["status", "payment_id"])
    return OK


def _complete_dj_application(order_id, gateway_payment_id, gateway_response, paid_amount_paise):
    from apps.commerce.models import DJApplicationFee

    with transaction.atomic():
        fee = DJApplicationFee.objects.select_for_update().filter(payment_id=order_id).first()
        if not fee:
            return NOT_FOUND
        if fee.status == "paid":
            return ALREADY
        if not _amount_ok(_paise(fee.amount), paid_amount_paise, order_id):
            return AMOUNT_MISMATCH
        fee.status = "paid"
        fee.paid_at = timezone.now()
        fee.payment_id = gateway_payment_id or order_id
        fee.save(update_fields=["status", "paid_at", "payment_id"])
        dj = fee.dj
        if dj.status == "pending_payment":
            dj.status = "pending_review"
            dj.save(update_fields=["status"])
    return OK


def _complete_pro_subscription(order_id, gateway_payment_id, gateway_response, paid_amount_paise):
    from apps.commerce.models import ProSubscriptionEvent

    with transaction.atomic():
        event = (
            ProSubscriptionEvent.objects.select_for_update()
            .filter(gateway_order_id=order_id, event_type="payment_initiated")
            .first()
        )
        if not event:
            return NOT_FOUND
        if ProSubscriptionEvent.objects.filter(gateway_order_id=order_id, event_type="payment_success").exists():
            return ALREADY
        if not _amount_ok(event.amount_paise, paid_amount_paise, order_id):
            return AMOUNT_MISMATCH
        profile = event.dj.profile
        now = timezone.now()
        days = 365 if event.plan_type == "annual" else 30
        start = max(now, profile.pro_expires_at or now)
        profile.is_pro_dj = True
        profile.pro_plan_type = event.plan_type
        profile.pro_started_at = profile.pro_started_at or now
        profile.pro_expires_at = start + timedelta(days=days)
        profile.pro_grace_ends_at = None
        profile.storage_quota_mb = max(profile.storage_quota_mb, 20480)
        profile.save()
        ProSubscriptionEvent.objects.create(
            dj=event.dj,
            event_type="payment_success",
            plan_type=event.plan_type,
            amount_paise=event.amount_paise,
            gateway=event.gateway,
            gateway_order_id=order_id,
            gateway_payment_id=gateway_payment_id,
        )
    return OK
