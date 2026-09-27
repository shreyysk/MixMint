import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from apps.commerce.models import WebhookLog

from .razorpay_gateway import RazorpayGateway
from .services import complete_order, fail_order

logger = logging.getLogger("mixmint")


@csrf_exempt
def razorpay_webhook(request):
    """
    Razorpay webhook. Configure in the dashboard with events `payment.captured`,
    `payment.failed`, `order.paid`, and the secret in RAZORPAY_WEBHOOK_SECRET.
    """
    if request.method != "POST":
        return HttpResponse(status=405)

    raw = request.body
    if not RazorpayGateway.verify_webhook(raw, request.headers.get("X-Razorpay-Signature", "")):
        logger.warning("Razorpay webhook: invalid signature.")
        return HttpResponse(status=401)

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponse(status=400)

    event = payload.get("event", "")
    entity = (payload.get("payload", {}).get("payment", {}) or {}).get("entity", {}) or {}
    order_id = entity.get("order_id") or (payload.get("payload", {}).get("order", {}) or {}).get("entity", {}).get("id")
    payment_id = entity.get("id", "")
    if not order_id:
        return HttpResponse(status=200)  # nothing we can match

    event_id = request.headers.get("X-Razorpay-Event-Id") or f"{event}:{payment_id or order_id}"
    log_key = f"razorpay:{event_id}"
    if WebhookLog.objects.filter(transaction_id=log_key, processed=True).exists():
        return HttpResponse(status=200)
    webhook_log, _ = WebhookLog.objects.get_or_create(
        transaction_id=log_key, defaults={"gateway": "razorpay", "payload": payload, "status": event}
    )

    try:
        if event in ("payment.captured", "order.paid"):
            result = complete_order(
                order_id,
                gateway_payment_id=payment_id,
                gateway_response=payload,
                paid_amount_paise=entity.get("amount"),
            )
            webhook_log.error = None if result in ("ok", "already_processed") else result
        elif event == "payment.failed":
            fail_order(order_id, payload)
        # payment.authorized is NOT a failure: capture follows (auto-capture or confirm view).
        webhook_log.processed = True
        webhook_log.save()
    except Exception as exc:
        logger.exception("Razorpay webhook processing failed for %s", order_id)
        webhook_log.error = str(exc)[:500]
        webhook_log.save()
        return HttpResponse(status=500)

    return HttpResponse(status=200)
