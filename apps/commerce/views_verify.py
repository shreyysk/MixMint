from decimal import Decimal
import json

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from apps.payments.utils import verify_payment as razorpay_verify
from apps.tracks.models import Track
from apps.albums.models import AlbumPack
from apps.accounts.models import Profile, DJProfile
from .models import Purchase, DEFAULT_CHECKOUT_FEE
from .services import MonetizationService

# Minimum prices enforced by MixMint [Spec §4]
MIN_TRACK_PRICE = Decimal('19.00')
MIN_ALBUM_PRICE = Decimal('49.00')


@csrf_exempt
def verify_purchase_view(request):
    """
    Unified purchase verification endpoint.
    Handles: track purchase, album purchase, re-download purchase (50% price).
    No subscriptions. No points. Ownership-based access only.
    [Spec P2 §5]
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        order_id = data.get('orderId')
        payment_id = data.get('paymentId')
        signature = data.get('signature')
        content_type = data.get('content_type')
        content_id = data.get('content_id')
        is_redownload = data.get('is_redownload', False)

        profile = request.user.profile

        # 1. Verify Razorpay signature
        if not razorpay_verify(payment_id, order_id, signature):
            return JsonResponse({'error': 'Invalid payment signature'}, status=403)

        # 2. Resolve content and seller
        seller = None
        original_price = Decimal('0.00')
        track_obj = None  # For collab lookup

        try:
            if content_type == 'track':
                item = Track.objects.get(id=content_id, is_active=True, is_deleted=False)
                seller = item.dj
                original_price = item.price
                track_obj = item
            elif content_type == 'zip':
                item = AlbumPack.objects.get(id=content_id, is_active=True, is_deleted=False)
                seller = item.dj
                original_price = item.price
            else:
                return JsonResponse({'error': 'Invalid content type'}, status=400)
        except (Track.DoesNotExist, AlbumPack.DoesNotExist):
            return JsonResponse({'error': 'Content not found or disabled'}, status=404)

        # 3. Calculate price
        price = original_price
        if is_redownload:
            existing = Purchase.objects.filter(
                user=profile, content_id=content_id, content_type=content_type,
                is_revoked=False, download_completed=True
            ).first()
            if not existing:
                return JsonResponse({'error': 'No completed purchase found for re-download'}, status=400)
            price = original_price * Decimal('0.50')  # 50% re-download [Spec §5]
        else:
            if Purchase.objects.filter(
                user=profile, content_id=content_id, content_type=content_type,
                is_revoked=False, is_redownload=False
            ).exists():
                return JsonResponse({'error': 'You already own this content.'}, status=400)

        # 4. Calculate revenue split
        checkout_fee = Decimal(str(DEFAULT_CHECKOUT_FEE))
        split = MonetizationService.calculate_revenue_split(seller, price)

        # 5. Create Purchase Record
        with transaction.atomic():
            purchase = Purchase.objects.create(
                user=profile,
                content_id=content_id,
                content_type=content_type,
                original_price=original_price,
                price_paid=price,
                checkout_fee=checkout_fee,
                commission=split['platform_amount'],
                dj_earnings=split['dj_amount'],
                platform_fee=split['platform_amount'],
                payment_id=payment_id,
                payment_order_id=order_id,
                seller=seller,
                is_redownload=is_redownload,
                is_completed=True,
            )

            # 6. Record Revenue Split (collab-aware) [Spec P2 §4]
            MonetizationService.record_revenue(
                seller, price, f"{content_type}_sale", payment_id, track=track_obj
            )

            # 7. Generate Invoice with GST
            MonetizationService.generate_invoice(purchase)

        return JsonResponse({
            'success': True,
            'message': 'Purchase verified and recorded successfully',
            'purchase_id': purchase.id
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
