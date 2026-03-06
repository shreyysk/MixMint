"""
MixMint Razorpay Webhook Handler [Spec P2 §5].

Handles payment.captured as the authoritative source of purchase confirmation.
This is the fallback to confirm_payment view — Razorpay guarantees delivery.
"""
import hmac
import hashlib
import json
import logging

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from apps.commerce.models import Purchase

logger = logging.getLogger(__name__)


@csrf_exempt
def razorpay_webhook(request):
    """
    Razorpay webhook — authoritative payment confirmation [Spec P2 §5].

    Handles:
    - payment.captured: Creates Purchase via revenue engine if not already created.
    - payment.failed: Logs failure for monitoring.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    signature = request.META.get('HTTP_X_RAZORPAY_SIGNATURE')
    if not signature:
        return JsonResponse({'error': 'Missing signature'}, status=400)

    # Verify HMAC-SHA256 signature [Spec P2 §5]
    expected_signature = hmac.new(
        key=settings.RAZORPAY_KEY_SECRET.encode(),
        msg=request.body,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        logger.warning("Razorpay webhook: invalid signature received.")
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    event = data.get('event')

    if event == 'payment.captured':
        _handle_payment_captured(data)
    elif event == 'payment.failed':
        _handle_payment_failed(data)

    return JsonResponse({'status': 'ok'})


def _handle_payment_captured(data):
    """
    Process a captured payment event from Razorpay [Spec P2 §5].
    Creates a Purchase record if not already created by the frontend confirm endpoint.
    Idempotent — safe to call multiple times for the same payment_id.
    """
    try:
        from apps.commerce.revenue_engine import create_purchase
        from apps.accounts.models import Profile

        entity = data['payload']['payment']['entity']
        payment_id = entity['id']
        order_id = entity.get('order_id', '')
        notes = entity.get('notes', {})

        content_id = notes.get('content_id')
        content_type = notes.get('content_type', 'track')
        user_email = notes.get('user_email', '')
        is_redownload = notes.get('is_redownload', 'False') == 'True'

        if not content_id or not user_email:
            logger.warning("Razorpay webhook: missing content_id or user_email in notes for payment %s", payment_id)
            return

        # Idempotency — skip if already processed by confirm_payment view
        if Purchase.objects.filter(payment_id=payment_id).exists():
            logger.info("Razorpay webhook: payment %s already processed, skipping.", payment_id)
            return

        # Resolve user profile
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(email=user_email)
            profile = user.profile
        except Exception:
            logger.error("Razorpay webhook: user not found for email %s (payment %s)", user_email, payment_id)
            return

        # Create purchase via revenue engine
        create_purchase(
            user_profile=profile,
            content_id=int(content_id),
            content_type=content_type,
            payment_id=payment_id,
            payment_order_id=order_id,
            is_redownload=is_redownload,
        )
        logger.info("Razorpay webhook: Purchase created from webhook for payment %s", payment_id)

    except Exception as exc:
        logger.exception("Razorpay webhook: error handling payment.captured — %s", exc)


def _handle_payment_failed(data):
    """Log failed payment for monitoring."""
    try:
        entity = data['payload']['payment']['entity']
        payment_id = entity.get('id', 'unknown')
        logger.warning("Razorpay webhook: payment FAILED — payment_id=%s", payment_id)
    except Exception:
        pass

