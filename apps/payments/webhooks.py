from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import hmac
import hashlib
import json

@csrf_exempt
def razorpay_webhook(request):
    """
    Webhook handler for Razorpay payment events.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    signature = request.META.get('HTTP_X_RAZORPAY_SIGNATURE')
    if not signature:
        return JsonResponse({'error': 'Missing signature'}, status=400)

    # Verify signature
    expected_signature = hmac.new(
        key=settings.RAZORPAY_KEY_SECRET.encode(),
        msg=request.body,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    data = json.loads(request.body)
    event = data.get('event')

    if event == 'payment.captured':
        # Logic to record purchase
        payment_data = data['payload']['payment']['entity']
        # purchase = Purchase.objects.create(...)
        pass
    
    return JsonResponse({'status': 'ok'})
