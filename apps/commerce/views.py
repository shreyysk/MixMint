from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from .models import Purchase, DJWallet, ProSubscriptionEvent, RefundRequest, Cart, CartItem
from .serializers import PurchaseSerializer, DJWalletSerializer, CartSerializer
import logging

logger = logging.getLogger(__name__)


class PurchaseViewSet(viewsets.ReadOnlyModelViewSet):
    """User's purchase history — only completed purchases [Spec §3.1]."""
    queryset = Purchase.objects.all()
    serializer_class = PurchaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Purchase.objects.filter(
            user=self.request.user.profile,
            status='paid',
        ).order_by('-created_at')


class DJWalletViewSet(viewsets.ReadOnlyModelViewSet):
    """DJ earnings wallet — DJs only [Spec §3.2]."""
    queryset = DJWallet.objects.all()
    serializer_class = DJWalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.profile.role != 'dj':
            return DJWallet.objects.none()
        try:
            dj_profile = self.request.user.profile.dj_profile
            return DJWallet.objects.filter(dj=dj_profile)
        except Exception:
            return DJWallet.objects.none()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def request_manual_payout(request):
    """
    DJ manually initiates a payout [Spec P2 §11, P3 §3.2].
    Requires 2FA verification code.
    """
    if request.user.profile.role != 'dj':
        return Response({'error': 'Only DJs can request payouts.'}, status=status.HTTP_403_FORBIDDEN)
    
    code = request.data.get('verification_code')
    if not code:
        return Response({'error': 'Verification code (OTP) is required.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        dj_profile = request.user.profile.dj_profile
        wallet = dj_profile.wallet
    except Exception:
        return Response({'error': 'DJ profile or wallet not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    # Verify OTP [Spec P2 §11]
    from apps.accounts.payout_auth import verify_payout_otp
    success, message = verify_payout_otp(dj_profile, code)
    if not success:
        return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
    
    # Process Payout
    from .payout_processor import _process_single_payout
    payout_amount = _process_single_payout(wallet)
    
    if not payout_amount:
        return Response({
            'error': 'Insufficient funds or payout threshold not reached.',
            'threshold': '₹500'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({
        'status': 'initiated',
        'message': f'Payout of ₹{payout_amount} initiated successfully.',
        'payout_amount': str(payout_amount)
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def open_dispute(request):
    """Initiates a formal dispute for a purchase [Imp 01]."""
    purchase_id = request.data.get('purchase_id')
    reason = request.data.get('reason')

    if not purchase_id or not reason:
        return Response({'error': 'purchase_id and reason are required.'}, status=400)

    try:
        purchase = Purchase.objects.get(id=purchase_id, user=request.user.profile)
    except Purchase.DoesNotExist:
        return Response({'error': 'Purchase not found.'}, status=404)

    from .models import PurchaseDispute
    dispute = PurchaseDispute.objects.create(
        purchase=purchase,
        user=request.user.profile,
        reason=reason
    )

    return Response({
        'status': 'dispute_opened',
        'dispute_id': dispute.id,
        'message': 'Dispute opened. Our support team will review it within 24-48 hours.'
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_library(request):
    """
    List all tracks/albums purchased by the user [Spec §3.1].
    Excludes revoked purchases.
    """
    purchases = Purchase.objects.filter(
        user=request.user.profile,
        status='paid',  # Only show successful purchases [Spec §3.1]
        is_revoked=False
    ).order_by('-created_at')
    
    serializer = PurchaseSerializer(purchases, many=True)
    return Response(serializer.data)
    
@login_required
def pro_landing(request):
    """MixMint Pro landing page [Section B]"""
    return render(request, 'commerce/pro_landing.html')


@login_required
@api_view(['POST'])
def activate_pro_trial(request):
    """Activates 7-day free trial for Pro Plan [Section B Step 5]"""
    profile = request.user.profile
    if profile.role != 'dj':
        return Response({'error': 'Only DJs can activate Pro Plan trials.'}, status=status.HTTP_403_FORBIDDEN)
    
    if profile.is_pro_dj:
        return Response({'error': 'You are already a Pro DJ.'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if they've used a trial before
    if ProSubscriptionEvent.objects.filter(dj=profile.dj_profile, event_type='trial_start').exists():
        return Response({'error': 'You have already used your free trial.'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        # Update Profile
        profile.is_pro_dj = True
        profile.pro_started_at = timezone.now()
        profile.pro_trial_ends_at = timezone.now() + timedelta(days=7)
        profile.pro_expires_at = profile.pro_trial_ends_at # Trial ends = expires if not paid
        profile.storage_quota_mb = 20480 # 20 GB [Spec P3 §1.5]
        profile.save()

        # Log Event
        ProSubscriptionEvent.objects.create(
            dj=profile.dj_profile,
            event_type='trial_start',
            plan_type='monthly', # Default
            amount_paise=0,
            gateway_order_id=f"TRIAL_{profile.user.id.hex[:8].upper()}"
        )

    return Response({
        'status': 'success',
        'message': 'Pro Plan trial activated! You now have 7 days of Pro features.',
        'expires_at': profile.pro_expires_at.isoformat()
    })


@login_required
@api_view(['POST'])
def request_refund(request):
    """
    Buyer requests a refund [Section C Fix 01].
    Automated if download not completed.
    """
    purchase_id = request.data.get('purchase_id')
    reason = request.data.get('reason', '')

    if not purchase_id:
        return Response({'error': 'Purchase ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        purchase = Purchase.objects.get(id=purchase_id, user=request.user.profile)
    except Purchase.DoesNotExist:
        return Response({'error': 'Purchase not found.'}, status=status.HTTP_404_NOT_FOUND)

    if purchase.status != 'paid':
        return Response({'error': 'Only paid purchases can be refunded.'}, status=status.HTTP_400_BAD_REQUEST)

    if RefundRequest.objects.filter(purchase=purchase).exists():
        return Response({'error': 'Refund request already exists for this purchase.'}, status=status.HTTP_400_BAD_REQUEST)

    # Automated refund eligibility check
    # [Spec §4.4: Byte verification status]
    eligible_for_auto = not purchase.download_completed

    with transaction.atomic():
        refund_req = RefundRequest.objects.create(
            purchase=purchase,
            reason=reason,
            eligible_for_auto_refund=eligible_for_auto,
            is_automated=eligible_for_auto,
            status='pending'
        )

        if eligible_for_auto:
            # Trigger automated refund
            from apps.payments.utils import get_gateway
            gateway = get_gateway()
            try:
                # PhonePe refund
                refund_result = gateway.process_refund(
                    original_transaction_id=purchase.gateway_payment_id or purchase.gateway_order_id,
                    amount_paise=purchase.amount_paise,
                    reason=f"Auto-refund: {reason}"
                )
                
                # Update purchase and refund request
                purchase.status = 'refunded'
                purchase.gateway_refund_id = refund_result['refund_id']
                purchase.save()
                
                refund_req.status = 'processed'
                refund_req.processed_at = timezone.now()
                refund_req.admin_notes = "Automatically approved: Download not completed."
                refund_req.save()
                
                return Response({
                    'status': 'success',
                    'message': 'Refund processed successfully (Automated).',
                    'automated': True
                })
            except Exception as e:
                logger.error(f"Refund failed for purchase {purchase_id}: {str(e)}")
                return Response({'error': f'Payment gateway refund failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({
        'status': 'pending',
        'message': 'Refund request submitted for admin review.',
        'automated': False
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def toggle_wishlist(request):
    """Imp 13: Toggle a track in/out of the buyer's wishlist."""
    from .models import Wishlist
    from apps.tracks.models import Track
    
    track_id = request.data.get('track_id')
    if not track_id:
        return Response({'error': 'track_id is required.'}, status=400)
    
    try:
        track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        return Response({'error': 'Track not found.'}, status=404)
    
    wishlist_item = Wishlist.objects.filter(user=request.user.profile, track=track)
    
    if wishlist_item.exists():
        wishlist_item.delete()
        return Response({'status': 'removed', 'is_wishlisted': False})
    else:
        # Prevent wishlisting owned tracks [Spec P3 §1.2]
        from .models import Purchase
        if Purchase.objects.filter(user=request.user.profile, content_id=track.id, content_type='track', status='paid').exists():
            return Response({'error': 'You already own this track.'}, status=400)
            
        Wishlist.objects.create(user=request.user.profile, track=track)
        return Response({'status': 'added', 'is_wishlisted': True})


class CartViewSet(viewsets.ModelViewSet):
    """API for managing shopping cart [Phase 3 Feature 3]."""
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user.profile, is_active=True)

    @action(detail=False, methods=['GET'])
    def current(self, request):
        """Get or create the user's active cart."""
        cart, _ = Cart.objects.get_or_create(user=request.user.profile, is_active=True)
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['POST'])
    def add_item(self, request):
        """Add an item to the active cart."""
        content_type = request.data.get('content_type')
        content_id = request.data.get('content_id')

        if not content_type or not content_id:
            return Response({'error': 'content_type and content_id are required'}, status=400)

        try:
            if content_type == 'track':
                from apps.tracks.models import Track
                content = Track.objects.get(id=content_id, is_active=True, is_deleted=False)
            elif content_type == 'album':
                from apps.albums.models import AlbumPack
                content = AlbumPack.objects.get(id=content_id, is_active=True, is_deleted=False)
            else:
                return Response({'error': 'Invalid content_type'}, status=400)
        except Exception:
            return Response({'error': 'Item not found'}, status=404)

        # Prevent purchasing already-owned content
        if Purchase.objects.filter(
            user=request.user.profile,
            content_type=content_type,
            content_id=content_id,
            status='paid',
            is_revoked=False
        ).exists():
            return Response({'error': 'You already own this item.'}, status=400)

        # Prevent DJ from buying own content
        if hasattr(request.user.profile, 'dj_profile') and request.user.profile.dj_profile == content.dj:
            return Response({'error': 'You cannot purchase your own content.'}, status=400)

        cart, _ = Cart.objects.get_or_create(user=request.user.profile, is_active=True)
        try:
            CartItem.objects.create(
                cart=cart,
                content_type=content_type,
                content_id=content_id,
                price=int(float(content.price) * 100)
            )
        except Exception:
            return Response({'error': 'Item is already in your cart.'}, status=400)

        return Response(self.get_serializer(cart).data)

    @action(detail=False, methods=['POST'])
    def remove_item(self, request):
        """Remove an item from the active cart."""
        item_id = request.data.get('item_id')
        if not item_id:
            return Response({'error': 'item_id is required'}, status=400)

        cart = Cart.objects.filter(user=request.user.profile, is_active=True).first()
        if not cart:
            return Response({'error': 'No active cart found.'}, status=404)

        deleted, _ = CartItem.objects.filter(id=item_id, cart=cart).delete()
        if not deleted:
            return Response({'error': 'Item not found in cart.'}, status=404)

        return Response(self.get_serializer(cart).data)

    @action(detail=False, methods=['POST'])
    def clear(self, request):
        """Clear all items from the active cart."""
        cart = Cart.objects.filter(user=request.user.profile, is_active=True).first()
        if cart:
            cart.items.all().delete()
            return Response(self.get_serializer(cart).data)
        return Response({'error': 'No active cart found.'}, status=404)
