"""
MixMint Payment Views [Spec P2 §5].

Handles:
- Payment initiation (Razorpay order creation)
- Payment confirmation (creates Purchase via revenue engine)
- Re-download payment flow
"""

import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import IntegrityError

from apps.payments.utils import create_order, verify_payment
from apps.commerce.revenue_engine import create_purchase
from apps.commerce.models import Purchase
from apps.tracks.models import Track
from apps.albums.models import AlbumPack


@login_required
def initiate_payment(request):
    """
    Create a Razorpay order for a track or album purchase [Spec P2 §5].
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    content_id = data.get('content_id')
    content_type = data.get('content_type', 'track')  # 'track' or 'album'
    is_redownload = data.get('is_redownload', False)

    # Back-compat normalization
    if content_type == 'zip':
        content_type = 'album'

    if not content_id:
        return JsonResponse({'error': 'content_id is required.'}, status=400)

    # Resolve content and price
    try:
        if content_type == 'track':
            content = Track.objects.get(id=content_id, is_active=True, is_deleted=False)
            price = float(content.price)
        elif content_type == 'album':
            content = AlbumPack.objects.get(id=content_id, is_active=True, is_deleted=False)
            price = float(content.price)
        elif content_type == 'dj_application':
            from apps.accounts.models import DJProfile
            from apps.commerce.models import DJApplicationFee
            content = DJProfile.objects.get(id=content_id)
            fee = DJApplicationFee.objects.get(dj=content, status='pending')
            price = float(fee.amount)
        else:
            return JsonResponse({'error': 'Invalid content_type.'}, status=400)
    except (Track.DoesNotExist, AlbumPack.DoesNotExist):
        return JsonResponse({'error': 'Content not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Item not found or already paid. {str(e)}'}, status=404)

    # Free tracks don't need payment
    if price <= 0:
        return JsonResponse({
            'free': True,
            'message': 'This content is free. No payment required.',
        })

    # Re-download pricing [Spec §4.3: 50% of original]
    if is_redownload:
        price = price * 0.5

    # Add checkout fee [Spec P3 §1.3]
    checkout_fee = 0.0
    if content_type in ['track', 'album']:
        from apps.admin_panel.models import PlatformSettings
        settings_obj = PlatformSettings.load()
        checkout_fee = float(settings_obj.buyer_platform_fee) if settings_obj.buyer_platform_fee_enabled else 0.0
    
    total_amount = price + checkout_fee

    # Create Razorpay Order
    receipt = f"{'re' if is_redownload else ''}purch_{content_type}_{content_id}"
    try:
        order = create_order(
            total_amount,
            receipt=receipt,
            notes={
                'content_id': str(content_id),
                'content_type': content_type,
                'user_email': request.user.email,
                'is_redownload': str(is_redownload),
            }
        )
    except Exception:
        return JsonResponse({'error': 'Payment gateway error.'}, status=500)

    return JsonResponse({
        'order_id': order['id'],
        'amount': order['amount'],
        'key': settings.RAZORPAY_KEY_ID,
        'content_price': price,
        'checkout_fee': checkout_fee,
        'total': total_amount,
        'currency': 'INR',
    })


@login_required
def confirm_payment(request):
    """
    Verify Razorpay payment and create Purchase record [Spec P2 §5].
    This is the critical path — creates Purchase, credits DJ wallet,
    generates invoice.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    payment_id = data.get('payment_id')
    order_id = data.get('order_id')
    signature = data.get('signature')
    content_id = data.get('content_id')
    content_type = data.get('content_type', 'track')
    is_redownload = data.get('is_redownload', False)

    # Back-compat normalization
    if content_type == 'zip':
        content_type = 'album'

    if not all([payment_id, order_id, signature, content_id]):
        return JsonResponse({'error': 'Missing required fields.'}, status=400)

    # Verify payment signature with Razorpay
    if not verify_payment(payment_id, order_id, signature):
        return JsonResponse({'error': 'Payment verification failed.'}, status=400)

    # Handle DJ Application fee separately
    if content_type == 'dj_application':
        from apps.accounts.models import DJProfile
        from apps.commerce.models import DJApplicationFee
        try:
            dj_profile = DJProfile.objects.get(id=content_id)
            fee = DJApplicationFee.objects.get(dj=dj_profile, status='pending')
            fee.status = 'paid'
            fee.payment_id = payment_id
            from django.utils import timezone
            fee.paid_at = timezone.now()
            fee.save()
            
            dj_profile.status = 'pending_review'
            dj_profile.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Application fee paid successfully. Application is now under review.',
            })
        except Exception as e:
            return JsonResponse({'error': f'Failed to process application fee. {str(e)}'}, status=500)

    # Prevent duplicate purchases
    if Purchase.objects.filter(payment_id=payment_id).exists():
        return JsonResponse({'error': 'Payment already processed.'}, status=400)

    # Create Purchase via revenue engine
    try:
        profile = request.user.profile
        purchase = create_purchase(
            user_profile=profile,
            content_id=content_id,
            content_type=content_type,
            payment_id=payment_id,
            payment_order_id=order_id,
            is_redownload=is_redownload,
        )

        return JsonResponse({
            'status': 'success',
            'purchase_id': purchase.id,
            'message': 'Payment verified. You can now download your content.',
        })

    except (Track.DoesNotExist, AlbumPack.DoesNotExist):
        return JsonResponse({'error': 'Content not found.'}, status=404)
    except IntegrityError:
        return JsonResponse({'error': 'Payment already processed.'}, status=400)
    except Exception:
        return JsonResponse({'error': 'Failed to process purchase.'}, status=500)
