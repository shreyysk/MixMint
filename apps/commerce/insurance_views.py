import json
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from apps.commerce.models import Purchase
from apps.downloads.models import DownloadInsurance
from apps.payments.utils import create_order, verify_payment

@login_required
def check_insurance_eligibility(request, purchase_id):
    """
    Check if a purchase is eligible for insurance [Spec §4.3].
    Available after 24 hours from original purchase.
    """
    try:
        purchase = Purchase.objects.get(id=purchase_id, user=request.user.profile)
    except Purchase.DoesNotExist:
        return JsonResponse({'error': 'Purchase not found.'}, status=404)

    if hasattr(purchase, 'insurance'):
        return JsonResponse({
            'eligible': False,
            'reason': 'Insurance already exists for this purchase.',
            'status': purchase.insurance.status
        })

    # 24-hour wait rule [Spec §4.3]
    wait_time = purchase.created_at + timedelta(hours=24)
    if timezone.now() < wait_time:
        remaining = wait_time - timezone.now()
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return JsonResponse({
            'eligible': False,
            'reason': f'Insurance available after 24 hours. Wait another {hours}h {minutes}m.',
            'available_at': wait_time.isoformat()
        })

    return JsonResponse({
        'eligible': True,
        'price': '₹49.00',  # Standard insurance price
        'content': purchase.content_id
    })

@login_required
def purchase_insurance(request, purchase_id):
    """
    Initiate insurance purchase flow [Spec §4.3].
    """
    try:
        purchase = Purchase.objects.get(id=purchase_id, user=request.user.profile)
    except Purchase.DoesNotExist:
        return JsonResponse({'error': 'Purchase not found.'}, status=404)

    if hasattr(purchase, 'insurance'):
        return JsonResponse({'error': 'Insurance already exists.'}, status=400)

    # Price for insurance (fixed ₹49 for now)
    price = Decimal('49.00')
    
    # Create Payment Order
    try:
        order = create_order(
            float(price),
            receipt=f"insurr_{purchase_id}",
            notes={'purchase_id': str(purchase_id), 'type': 'insurance'}
        )
        return JsonResponse({
            'order_id': order['id'],
            'amount': order['amount'],
            'currency': 'INR'
        })
    except Exception:
        return JsonResponse({'error': 'Payment gateway error.'}, status=500)

@login_required
def verify_insurance_payment(request):
    """
    Verify Razorpay payment and activate insurance [Spec §4.3].
    """

    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method.'}, status=400)
        
    try:
        data = json.loads(request.body)
        payment_id = data.get('payment_id')
        order_id = data.get('order_id')
        signature = data.get('signature')
        purchase_id = data.get('purchase_id')
    except (json.JSONDecodeError, TypeError, AttributeError):
        return JsonResponse({'error': 'Invalid request data.'}, status=400)

    if not verify_payment(payment_id, order_id, signature):
        return JsonResponse({'error': 'Payment verification failed.'}, status=400)

    try:
        purchase = Purchase.objects.get(id=purchase_id, user=request.user.profile)
    except Purchase.DoesNotExist:
        return JsonResponse({'error': 'Purchase not found.'}, status=404)

    # Activate Insurance
    insurance, created = DownloadInsurance.objects.get_or_create(
        purchase=purchase,
        defaults={
            'user': request.user.profile,
            'content_id': purchase.content_id,
            'content_type': purchase.content_type,
            'insurance_price': Decimal('49.00'),
            'payment_id': payment_id,
            'status': 'active'
        }
    )

    return JsonResponse({
        'status': 'success',
        'message': 'Download Insurance activated! You now have unlimited free re-downloads for this content.'
    })
