import json
import base64
import logging
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from uuid import uuid4

from apps.commerce.models import Purchase, WebhookLog

logger = logging.getLogger(__name__)

@csrf_exempt
def phonepe_webhook(request):
    """
    PhonePe server-to-server notification handler [Section A Step 3]
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    # Get signature from header
    x_verify = request.headers.get('X-VERIFY', '')

    # Get payload
    try:
        body = request.body.decode('utf-8')
        data = json.loads(body)
        payload_base64 = data.get('response', '')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponse(status=400)

    # Verify signature
    gateway = settings.ACTIVE_GATEWAY
    if not gateway.verify_payment(payload_base64, x_verify):
        logger.warning(f"PhonePe webhook: invalid signature received. X-VERIFY: {x_verify}")
        return HttpResponse(status=401)

    # Decode payload
    try:
        payload_json = base64.b64decode(payload_base64).decode()
        payload = json.loads(payload_json)
    except Exception as e:
        logger.error(f"PhonePe webhook: failed to decode payload. {str(e)}")
        return HttpResponse(status=400)

    # Extract transaction details
    transaction_id = payload.get('data', {}).get('merchantTransactionId')
    payment_status = payload.get('code', '')

    # Idempotency check
    if WebhookLog.objects.filter(transaction_id=transaction_id, processed=True).exists():
        return HttpResponse(status=200)

    # Log webhook
    webhook_log, _ = WebhookLog.objects.get_or_create(
        transaction_id=transaction_id,
        defaults={
            'gateway': 'phonepe',
            'payload': payload,
            'status': payment_status
        }
    )

    # Process based on status
    try:
        if payment_status == 'PAYMENT_SUCCESS':
            _process_successful_payment(transaction_id, payload)
        elif payment_status in ['PAYMENT_DECLINED', 'PAYMENT_ERROR']:
            _process_failed_payment(transaction_id, payload)
        
        webhook_log.processed = True
        webhook_log.save()
    except Exception as e:
        logger.exception(f"PhonePe webhook: error processing status {payment_status} for {transaction_id}")
        webhook_log.error = str(e)
        webhook_log.save()
        # Return 200 anyway so PhonePe stops retrying if it's a code error, 
        # or we might want to return 500 for them to retry. PhonePe usually retries on non-200.
        # But for now, 200 because we logged the error.

    return HttpResponse(status=200)

def _process_successful_payment(transaction_id, payload):
    data = payload.get('data', {})
    gateway_payment_id = data.get('transactionId')
    
    with transaction.atomic():
        try:
            purchase = Purchase.objects.get(gateway_order_id=transaction_id)
            if purchase.status != 'paid':
                purchase.status = 'paid'
                purchase.gateway_payment_id = gateway_payment_id
                purchase.gateway_response = payload
                purchase.paid_at = timezone.now() # Need to import timezone or use django.utils.timezone
                purchase.is_completed = True
                purchase.save()
                
                # TODO: Trigger post-purchase actions (email, invoice, earnings)
        except Purchase.DoesNotExist:
            logger.error(f"PhonePe webhook: purchase not found for Transaction ID {transaction_id}")

def _process_failed_payment(transaction_id, payload):
    try:
        purchase = Purchase.objects.get(gateway_order_id=transaction_id)
        if purchase.status == 'pending':
            purchase.status = 'failed'
            purchase.gateway_response = payload
            purchase.save()
    except Purchase.DoesNotExist:
        pass

# Legacy Razorpay webhook (keep for compatibility if needed, or redirect)
@csrf_exempt
def razorpay_webhook(request):
    from .webhooks_razorpay import razorpay_webhook as original_handler
    return original_handler(request)
