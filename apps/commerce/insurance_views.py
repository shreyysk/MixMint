"""
Download Insurance [Spec §4.3]: ₹49 add-on for a paid purchase that unlocks
unlimited free re-downloads. Paid through the normal gateway order flow and
activated by apps.payments.services.complete_order (callback/webhook/confirm).
"""

import uuid
from datetime import timedelta
from decimal import Decimal

from django.http import JsonResponse
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes

from apps.commerce.models import Purchase
from apps.downloads.models import DownloadInsurance

INSURANCE_PRICE = Decimal("49.00")


def _paid_purchase(request, purchase_id):
    return Purchase.objects.filter(
        id=purchase_id, user=request.user.profile, status="paid", is_revoked=False, is_redownload=False
    ).first()


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def check_insurance_eligibility(request, purchase_id):
    """Available 24 hours after the original purchase."""
    purchase = _paid_purchase(request, purchase_id)
    if not purchase:
        return JsonResponse({"error": "Purchase not found."}, status=404)

    ins = getattr(purchase, "insurance", None)
    if ins and ins.status == "active":
        return JsonResponse({"eligible": False, "reason": "Insurance is already active.", "status": ins.status})

    wait_until = (purchase.paid_at or purchase.created_at) + timedelta(hours=24)
    if timezone.now() < wait_until:
        remaining = wait_until - timezone.now()
        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        return JsonResponse(
            {
                "eligible": False,
                "reason": f"Insurance available after 24 hours. Wait another {hours}h {remainder // 60}m.",
                "available_at": wait_until.isoformat(),
            }
        )
    return JsonResponse({"eligible": True, "price": str(INSURANCE_PRICE), "content": purchase.content_id})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def purchase_insurance(request, purchase_id):
    """Create a gateway order for insurance; the row activates only when payment completes."""
    from apps.payments.utils import get_gateway
    from apps.payments.views import _gateway_error, _gateway_payload

    purchase = _paid_purchase(request, purchase_id)
    if not purchase:
        return JsonResponse({"error": "Purchase not found."}, status=404)
    if timezone.now() < (purchase.paid_at or purchase.created_at) + timedelta(hours=24):
        return JsonResponse({"error": "Insurance is available 24 hours after purchase."}, status=400)

    ins = getattr(purchase, "insurance", None)
    if ins and ins.status == "active":
        return JsonResponse({"error": "Insurance already active."}, status=400)

    amount_paise = int(INSURANCE_PRICE * 100)
    internal_id = f"INS_{uuid.uuid4().hex[:14].upper()}"
    try:
        gateway = get_gateway(request.data.get("gateway") if hasattr(request, "data") else None)
        result = gateway.create_order(
            amount_paise=amount_paise,
            order_id=internal_id,
            metadata={"user_id": str(request.user.id), "purchase_id": str(purchase.id), "purpose": "insurance"},
        )
    except Exception as exc:
        return _gateway_error(exc)
    order_id = result.get("gateway_order_id") or result.get("order_id") or internal_id

    DownloadInsurance.objects.update_or_create(
        purchase=purchase,
        defaults={
            "user": request.user.profile,
            "content_id": purchase.content_id,
            "content_type": purchase.content_type,
            "insurance_price": INSURANCE_PRICE,
            "payment_id": order_id,
            "status": "pending",
        },
    )
    payload = _gateway_payload(result, order_id, amount_paise)
    payload["description"] = "Download Insurance"
    return JsonResponse(payload)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def verify_insurance_payment(request):
    """Razorpay checkout result for an insurance order -> shared confirm path."""
    from apps.payments.views import razorpay_confirm

    return razorpay_confirm(request._request)
