import base64
import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from apps.commerce.models import WebhookLog

from .services import complete_order, fail_order

logger = logging.getLogger("mixmint")

SUCCESS_CODES = ("PAYMENT_SUCCESS",)
FAILURE_CODES = ("PAYMENT_DECLINED", "PAYMENT_ERROR", "TIMED_OUT", "PAYMENT_CANCELLED")


@csrf_exempt
def phonepe_webhook(request):
    """PhonePe server-to-server callback [Section A Step 3]. Always verified with the PhonePe salt."""
    if request.method != "POST":
        return HttpResponse(status=405)

    x_verify = request.headers.get("X-VERIFY", "")
    try:
        data = json.loads(request.body.decode("utf-8"))
        payload_base64 = data.get("response", "")
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
        return HttpResponse(status=400)

    try:
        from .phonepe import PhonePeGateway

        gateway = PhonePeGateway()
    except Exception:
        logger.error("PhonePe webhook received but PhonePe is not configured.")
        return HttpResponse(status=503)

    if not gateway.verify_payment(payload_base64, x_verify):
        logger.warning("PhonePe webhook: invalid signature.")
        return HttpResponse(status=401)

    try:
        payload = json.loads(base64.b64decode(payload_base64).decode())
    except Exception:
        logger.error("PhonePe webhook: undecodable payload.")
        return HttpResponse(status=400)

    pdata = payload.get("data", {}) or {}
    order_id = pdata.get("merchantTransactionId")
    code = payload.get("code", "")
    if not order_id:
        return HttpResponse(status=400)

    log_key = f"phonepe:{order_id}:{code}"
    if WebhookLog.objects.filter(transaction_id=log_key, processed=True).exists():
        return HttpResponse(status=200)
    webhook_log, _ = WebhookLog.objects.get_or_create(
        transaction_id=log_key, defaults={"gateway": "phonepe", "payload": payload, "status": code}
    )

    try:
        if code in SUCCESS_CODES:
            result = complete_order(
                order_id,
                gateway_payment_id=pdata.get("transactionId", ""),
                gateway_response=payload,
                paid_amount_paise=pdata.get("amount"),
            )
            webhook_log.error = None if result in ("ok", "already_processed") else result
        elif code in FAILURE_CODES:
            fail_order(order_id, payload)
        webhook_log.processed = True
        webhook_log.save()
    except Exception as exc:
        logger.exception("PhonePe webhook processing failed for %s", order_id)
        webhook_log.error = str(exc)[:500]
        webhook_log.save()
        return HttpResponse(status=500)  # let PhonePe retry

    return HttpResponse(status=200)


@csrf_exempt
def razorpay_webhook(request):
    from .webhooks_razorpay import razorpay_webhook as handler

    return handler(request)
