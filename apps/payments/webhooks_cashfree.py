"""Cashfree Payment Gateway webhook. Signature-checked; the Get Order API then decides what happened."""

import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from apps.commerce.models import WebhookLog

logger = logging.getLogger("mixmint")


@csrf_exempt
def cashfree_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    try:
        from .cashfree_pg import CashfreeGateway

        gateway = CashfreeGateway()
    except Exception:
        logger.error("Cashfree webhook received but Cashfree is not configured.")
        return HttpResponse(status=503)
    raw = request.body or b""
    if not gateway.verify_payment(raw, request.headers.get("x-webhook-signature", ""), request.headers.get("x-webhook-timestamp", "")):
        logger.warning("Cashfree webhook: bad signature.")
        return HttpResponse(status=401)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return HttpResponse(status=400)
    kind = str(data.get("type") or "")
    order_id = ((data.get("data") or {}).get("order") or {}).get("order_id")
    if kind.startswith("PAYMENT_") and order_id:
        log_key = f"cashfree:{order_id}:{kind}"
        if WebhookLog.objects.filter(transaction_id=log_key, processed=True).exists():
            return HttpResponse(status=200)
        log, _ = WebhookLog.objects.get_or_create(transaction_id=log_key, defaults={"gateway": "cashfree", "payload": data, "status": kind})
        try:
            from .services import fail_order
            from .views import _fulfil_from_status

            outcome = _fulfil_from_status(order_id, "cashfree")
            if outcome == "pending" and kind in ("PAYMENT_FAILED_WEBHOOK", "PAYMENT_USER_DROPPED_WEBHOOK"):
                fail_order(order_id, data)  # releases held copies; a new attempt makes a new order
                outcome = "failed"
            log.processed = outcome in ("success", "failed")
            log.error = None
            log.save()
        except Exception as exc:
            logger.exception("Cashfree webhook processing failed for %s", order_id)
            log.error = str(exc)[:500]
            log.save()
            return HttpResponse(status=500)  # Cashfree retries
    elif kind.startswith("REFUND_") and "FAIL" in json.dumps(data).upper():
        try:
            from apps.admin_panel.telegram import notify_admins

            notify_admins(f"Cashfree refund problem for order {order_id or '?'}: check the Cashfree dashboard.")
        except Exception:
            pass
    return HttpResponse(status=200)
