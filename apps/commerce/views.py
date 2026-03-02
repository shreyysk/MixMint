from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import Purchase, DJWallet
from .serializers import PurchaseSerializer, DJWalletSerializer


class PurchaseViewSet(viewsets.ReadOnlyModelViewSet):
    """User's purchase history — only completed purchases [Spec §3.1]."""
    queryset = Purchase.objects.all()
    serializer_class = PurchaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Purchase.objects.filter(
            user=self.request.user.profile,
            is_completed=True,
            download_completed=True,  # Only show after successful download [Spec §3.1]
        ).order_by('-created_at')


class DJWalletViewSet(viewsets.ReadOnlyModelViewSet):
    """DJ earnings wallet — DJs only [Spec §3.2]."""
    queryset = DJWallet.objects.all()
    serializer_class = DJWalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != 'dj':
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
    if request.user.role != 'dj':
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

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_library(request):
    """
    List all tracks/albums purchased by the user [Spec §3.1].
    Excludes revoked purchases.
    """
    purchases = Purchase.objects.filter(
        user=request.user.profile,
        is_completed=True,
        is_revoked=False
    ).order_by('-created_at')
    
    serializer = PurchaseSerializer(purchases, many=True)
    return Response(serializer.data)
