import json
import hmac
import hashlib
import logging
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.commerce.models import Purchase, WebhookLog

logger = logging.getLogger(__name__)


@csrf_exempt
def razorpay_webhook(request):
    """
    Razorpay server-to-server webhook handler.
    """
    if request.method != "POST":
        return HttpResponse(status=405)

    # Get signature from header
    x_signature = request.headers.get("X-Razorpay-Signature", "")

    # Get payload
    try:
        body = request.body.decode("utf-8")
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponse(status=400)

    # Verify signature
    expected_signature = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_signature, x_signature):
        logger.warning(f"Razorpay webhook: invalid signature received. X-Signature: {x_signature}")
        return HttpResponse(status=401)

    # Extract event details
    event = payload.get("event", "")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = payment_entity.get("order_id")
    payment_id = payment_entity.get("id")
    payment_status = payment_entity.get("status")
    if not payment_id:
        logger.warning(f"Razorpay webhook: missing payment id for event {event}.")
        return HttpResponse(status=200)  # nothing trackable; don't retry

    # Idempotency check
    if WebhookLog.objects.filter(transaction_id=payment_id, processed=True).exists():
        return HttpResponse(status=200)

    # Log webhook
    webhook_log, _ = WebhookLog.objects.get_or_create(
        transaction_id=payment_id, defaults={"gateway": "razorpay", "payload": payload, "status": payment_status}
    )

    try:
        if event == "payment.captured":
            _process_successful_payment(order_id, payment_id, payload)
        elif event in ["payment.failed", "payment.authorized"]:
            _process_failed_payment(order_id, payment_id, payload)

        webhook_log.processed = True
        webhook_log.save()
    except Exception as e:
        logger.exception(f"Razorpay webhook: error processing event {event} for {payment_id}")
        webhook_log.error = str(e)
        webhook_log.save()

    return HttpResponse(status=200)


def _process_successful_payment(order_id, payment_id, payload):
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    with transaction.atomic():
        purchases = Purchase.objects.filter(gateway_order_id=order_id)
        if not purchases.exists():
            logger.error(f"Razorpay webhook: purchases not found for Order ID {order_id}")
            return

        # Amount check: captured paise must equal what we charged across the order.
        captured = payment_entity.get("amount")
        if captured is not None:
            from decimal import Decimal

            expected = 0
            for p in purchases:
                if p.amount_paise is not None:
                    expected += int(p.amount_paise)
                else:
                    expected += int((p.price_paid or Decimal("0.00")) * 100)
            try:
                if int(captured) != expected:
                    logger.error(
                        f"Razorpay webhook: amount mismatch for {order_id} "
                        f"(captured {captured} vs expected {expected}). NOT marking paid."
                    )
                    return
            except (TypeError, ValueError):
                logger.error(f"Razorpay webhook: unparseable amount {captured!r} for {order_id}.")
                return

        for purchase in purchases:
            if purchase.status != "paid":
                purchase.status = "paid"
                purchase.gateway_payment_id = payment_id
                purchase.gateway_response = payload
                purchase.paid_at = timezone.now()
                purchase.is_completed = True
                purchase.save()

                from apps.commerce.services import MonetizationService

                MonetizationService.complete_purchase(purchase)


def _process_failed_payment(order_id, payment_id, payload):
    for purchase in Purchase.objects.filter(gateway_order_id=order_id, status="pending"):
        purchase.status = "failed"
        purchase.gateway_response = payload
        purchase.save()
