import json
import uuid
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone

from apps.commerce.models import Purchase
from apps.tracks.models import Track
from apps.albums.models import AlbumPack
# from apps.commerce.revenue_engine import distribute_earnings # Placeholder for now

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_device_hash(request):
    # Simplified device hash for now
    return request.META.get('HTTP_USER_AGENT', 'unknown')

def run_fraud_checks(user_id, data):
    # Placeholder for fraud detection
    return True, 'low', []

def calculate_total_price_paise(content, is_redownload=False):
    price = float(content.price)
    if is_redownload:
        price = price * 0.5
    
    # Add platform fee
    from apps.admin_panel.models import PlatformSettings
    settings_obj = PlatformSettings.load()
    platform_fee = float(settings_obj.buyer_platform_fee) if settings_obj.buyer_platform_fee_enabled else 0.0
    
    return int((price + platform_fee) * 100)

def get_content_object(content_id, content_type):
    if content_type == 'track':
        return Track.objects.get(id=content_id, is_active=True, is_deleted=False)
    elif content_type in ('album', 'zip'):
        return AlbumPack.objects.get(id=content_id, is_active=True, is_deleted=False)
    raise ValueError(f"Invalid content type: {content_type}")


@login_required
@require_POST
def initiate_purchase(request):
    """
    Buyer clicks "Buy & Download" -> this view creates order [Section A Step 1]
    """
    try:
        data = json.loads(request.body)
        content_id = data.get('content_id')
        content_type = data.get('content_type') # track|album
        is_redownload = data.get('is_redownload', False)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # 1. Duplicate Purchase Guard [Gap 20]
    if not is_redownload:
        existing_purchase = Purchase.objects.filter(
            user=request.user.profile,
            content_type=content_type,
            content_id=content_id,
            status='paid', # Standardizing to 'paid' check
            is_revoked=False
        ).exists()
        if existing_purchase:
            return JsonResponse({
                'error': f'You already own this {content_type}.',
                'already_owned': True
            }, status=400)

    # 1.5 Prevent DJ from buying their own track
    try:
        content_obj = get_content_object(content_id, content_type)
        if hasattr(request.user.profile, 'dj_profile') and request.user.profile.dj_profile == content_obj.dj:
            return JsonResponse({
                'error': 'You cannot purchase your own content.',
                'self_purchase': True
            }, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)

    # 2. Run fraud checks
    fraud_result, risk, flags = run_fraud_checks(
        request.user.id,
        {
            'ip_address': get_client_ip(request),
            'device_hash': get_device_hash(request),
            'content_id': content_id
        }
    )
    if not fraud_result:
        return JsonResponse({'error': 'Purchase could not be processed'}, status=403)

    # 2. Get content + calculate price server-side
    try:
        amount_paise = calculate_total_price_paise(content_obj, is_redownload)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)

    # 3. Create pending purchase record in atomic block
    order_id = f"MM_{uuid.uuid4().hex[:16].upper()}"
    
    with transaction.atomic():
        purchase = Purchase.objects.create(
            user=request.user.profile,
            content_type=content_type,
            content_id=content_id,
            seller=content_obj.dj,
            gateway_order_id=order_id,
            payment_gateway=settings.ACTIVE_GATEWAY.__class__.__name__.lower().replace('gateway', ''),
            amount_paise=amount_paise,
            original_price=content_obj.price,
            price_paid=amount_paise / 100.0,
            status='pending',
        )

        # 4. Create Gateway order
        gateway = settings.ACTIVE_GATEWAY
        try:
            result = gateway.create_order(
                amount_paise=amount_paise,
                order_id=order_id,
                metadata={
                    'user_id': str(request.user.id),
                    'purchase_id': str(purchase.id)
                }
            )
            return JsonResponse({
                'redirect_url': result['redirect_url'],
                'order_id': order_id
            })
        except Exception as e:
            purchase.status = 'failed'
            purchase.save()
            transaction.set_rollback(True) # Force rollback of the record if gateway fails
            return JsonResponse({'error': f'Payment gateway error: {str(e)}'}, status=500)

def payment_callback(request):
    """
    User lands here after PhonePe payment page. [Section A Step 2]
    Handles both single-item and cart-based purchases.
    """
    order_id = request.GET.get('order_id')
    if not order_id:
        return HttpResponseRedirect('/payment/failed/')

    # Verify status via API
    gateway = settings.ACTIVE_GATEWAY
    status_data = gateway.get_payment_status(order_id)

    # Find all purchases with this order_id (could be one or many)
    purchases = Purchase.objects.filter(gateway_order_id=order_id)
    if not purchases.exists():
        return HttpResponseRedirect('/payment/failed/')

    if status_data['success'] and status_data['status'] == 'PAYMENT_SUCCESS':
        for purchase in purchases:
            handle_payment_success(purchase, status_data)
        
        # If it was a cart purchase, redirect to multi-purchase view or downloads
        first_purchase = purchases.first()
        return HttpResponseRedirect(f'/downloads/?order_id={order_id}')
    else:
        for purchase in purchases:
            handle_payment_failure(purchase, status_data)
        return HttpResponseRedirect(f'/payment/failed/?order_id={order_id}')

def handle_payment_success(purchase, gateway_status):
    with transaction.atomic():
        if purchase.status != 'paid':
            purchase.status = 'paid'
            purchase.gateway_payment_id = gateway_status['transaction_id']
            purchase.gateway_response = gateway_status['gateway_response']
            purchase.paid_at = timezone.now()
            purchase.is_completed = True # Back-compat
            purchase.save()

            # Distribute earnings to DJ wallet (Phase 2 ??9)
            from apps.commerce.revenue_engine import credit_dj_wallets, calculate_revenue_split
            
            # Re-calculate or fetch split for this purchase
            # Note: amount_paise is stored, price_paid is decimal
            split = calculate_revenue_split(
                price=purchase.price_paid, 
                dj_profile=purchase.seller,
                content=None, # In case of generic purchase
                content_type=purchase.content_type
            )
            credit_dj_wallets(purchase, purchase.seller, split)
            
            # Check if DJ is now eligible for Verified Badge [Imp 06]
            if purchase.seller:
                try:
                    from apps.accounts.utils import check_verification_eligibility
                    check_verification_eligibility(purchase.seller)
                except ImportError:
                    pass
            
            # Notify DJ via Push/In-App
            try:
                from apps.core.push_notifications import PushNotificationService
                content_type_label = purchase.get_content_type_display() if hasattr(purchase, 'get_content_type_display') else purchase.content_type
                PushNotificationService.notify_sale(
                    dj_profile=purchase.seller,
                    track_title=f"{content_type_label} #{purchase.content_id}", # Fallback title
                    amount=purchase.dj_revenue
                )
            except Exception:
                pass

    return HttpResponseRedirect(f'/downloads/?purchase_id={purchase.id}')

def handle_payment_failure(purchase, gateway_status):
    purchase.status = 'failed'
    purchase.gateway_response = gateway_status['gateway_response']
    purchase.save()
    return HttpResponseRedirect(f'/payment/failed/?order_id={purchase.gateway_order_id}')


@login_required
def cart_page(request):
    """Render the cart page [Phase 3 Feature 3]."""
    from django.shortcuts import render
    return render(request, 'commerce/cart.html')


@login_required
@require_POST
def cart_checkout(request):
    """
    Initiate payment for all items in the cart [Phase 3 Feature 3].
    Uses tiered bundle discounts.
    """
    try:
        data = json.loads(request.body)
        cart_id = data.get('cart_id')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    from apps.commerce.models import Cart, CartItem
    try:
        cart = Cart.objects.get(id=cart_id, user=request.user.profile, is_active=True)
    except Cart.DoesNotExist:
        return JsonResponse({'error': 'Cart not found.'}, status=404)

    items = list(cart.items.all())
    if not items:
        return JsonResponse({'error': 'Cart is empty.'}, status=400)

    total_paise = int(cart.final_total * 100) # Ensure paise conversion
    if total_paise <= 0:
        return JsonResponse({'error': 'Cart total is too low for processing.'}, status=400)

    order_id = f"MMC_{uuid.uuid4().hex[:14].upper()}"
    pending_purchases = []
    
    with transaction.atomic():
        try:
            for item in items:
                item_content = get_content_object(item.content_id, item.content_type)
                p = Purchase.objects.create(
                    user=request.user.profile,
                    content_type=item.content_type,
                    content_id=item.content_id,
                    seller=item_content.dj,
                    gateway_order_id=order_id,
                    payment_gateway=settings.ACTIVE_GATEWAY.__class__.__name__.lower().replace('gateway', ''),
                    amount_paise=item.price, # Stored as paise in CartItem
                    original_price=item_content.price,
                    price_paid=item.price / 100.0,
                    cart_id=str(cart.id),
                    status='pending',
                    discount_applied=cart.discount_percentage
                )
                pending_purchases.append(p)
        except Exception as e:
            return JsonResponse({'error': f'Error preparing checkout: {str(e)}'}, status=500)

        gateway = settings.ACTIVE_GATEWAY
        try:
            result = gateway.create_order(
                amount_paise=total_paise,
                order_id=order_id,
                metadata={
                    'user_id': str(request.user.id),
                    'cart_id': str(cart.id),
                    'purchase_ids': [str(p.id) for p in pending_purchases]
                }
            )
            # ONLY mark cart inactive if order creation succeeded
            cart.is_active = False 
            cart.save()
            return JsonResponse({'redirect_url': result['redirect_url'], 'order_id': order_id})
        except Exception as e:
            # Atomic rollback will handle purchase records if we raise or set_rollback
            transaction.set_rollback(True)
            return JsonResponse({'error': f'Payment gateway error: {str(e)}'}, status=500)
