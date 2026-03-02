"""
DJ Application views — handles the DJ onboarding flow [Spec §7, P2 §2].

Flow:
1. User submits DJ application
2. Admin approves/rejects
3. On approval: DJProfile + DJWallet created
"""

from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from apps.accounts.models import Profile, DJProfile
from apps.commerce.models import DJWallet, DJApplicationFee


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_as_dj(request):
    """
    Submit a DJ application [Spec §7].
    Checks:
    - User is not already a DJ
    - No pending application exists
    - Application fee paid (if enabled by admin)
    - FREE for first 3 months [Spec §7]
    """
    user = request.user
    profile = user.profile

    # Already a DJ?
    if user.role == 'dj':
        return Response({'error': 'You are already a DJ.'}, status=status.HTTP_400_BAD_REQUEST)

    # Already has a DJProfile?
    if hasattr(profile, 'dj_profile'):
        return Response(
            {'error': 'You already have a DJ profile.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check required fields
    dj_name = request.data.get('dj_name', '').strip()
    slug = request.data.get('slug', '').strip().lower()
    bio = request.data.get('bio', '').strip()
    genres = request.data.get('genres', [])
    legal_agreement = request.data.get('legal_agreement_accepted', False)

    if not dj_name:
        return Response({'error': 'DJ name is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not slug:
        return Response({'error': 'URL slug is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not legal_agreement:
        return Response(
            {'error': 'You must accept the legal agreement to proceed.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check slug uniqueness
    if DJProfile.objects.filter(slug=slug).exists():
        return Response(
            {'error': 'This URL slug is already taken.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check application fee requirement [Spec §7: ₹99 intro, free first 3 months]
    from apps.admin_panel.models import SystemSetting
    
    intro_period_end = settings.PLATFORM_LAUNCH_DATE + timedelta(days=90)
    is_within_free_3_months = timezone.now() < intro_period_end
    
    fee_enabled = True
    if is_within_free_3_months:
        fee_enabled = False
    else:
        try:
            fee_setting = SystemSetting.objects.get(key='dj_application_fee_enabled')
            fee_enabled = fee_setting.value.get('enabled', True)
        except SystemSetting.DoesNotExist:
            pass

    # Create DJProfile in pending status
    dj_profile = DJProfile.objects.create(
        profile=profile,
        dj_name=dj_name,
        slug=slug,
        bio=bio,
        genres=genres if isinstance(genres, list) else [],
        status='pending',
        legal_agreement_accepted=legal_agreement,
        application_fee_paid=not fee_enabled,  # Auto-mark paid if fee disabled/waived
    )

    # Create application fee record if fee is enabled
    if fee_enabled:
        DJApplicationFee.objects.create(
            dj=dj_profile,
            amount=settings.DJ_APPLICATION_FEE,
            status='pending',
        )
        return Response({
            'status': 'pending',
            'message': f'Application submitted. Please pay ₹{settings.DJ_APPLICATION_FEE} application fee.',
            'fee_required': True,
            'fee_amount': settings.DJ_APPLICATION_FEE,
            'dj_profile_id': dj_profile.id,
        }, status=status.HTTP_201_CREATED)
    else:
        return Response({
            'status': 'pending',
            'message': 'Application submitted. Waiting for admin approval.',
            'fee_required': False,
            'dj_profile_id': dj_profile.id,
        }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_approve_dj(request, dj_profile_id):
    """
    Admin approves a DJ application [Spec §3.3].
    Creates DJWallet and updates user role.
    """
    try:
        dj_profile = DJProfile.objects.get(id=dj_profile_id)
    except DJProfile.DoesNotExist:
        return Response({'error': 'DJ profile not found.'}, status=status.HTTP_404_NOT_FOUND)

    if dj_profile.status == 'approved':
        return Response({'error': 'Already approved.'}, status=status.HTTP_400_BAD_REQUEST)

    # Check fee paid (if required)
    if not dj_profile.application_fee_paid:
        try:
            fee = dj_profile.application_fee
            if fee.status != 'paid' and fee.status != 'waived':
                return Response(
                    {'error': 'Application fee not paid yet.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except DJApplicationFee.DoesNotExist:
            pass  # Fee not required

    # Approve
    dj_profile.status = 'approved'
    dj_profile.save(update_fields=['status'])

    # Update user role
    user = dj_profile.profile.user
    user.role = 'dj'
    user.save(update_fields=['role'])

    # Create DJ Wallet [Spec P2 §9]
    DJWallet.objects.get_or_create(dj=dj_profile)

    return Response({
        'status': 'approved',
        'message': f'{dj_profile.dj_name} has been approved as a DJ.',
        'dj_profile_id': dj_profile.id,
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_reject_dj(request, dj_profile_id):
    """Admin rejects a DJ application [Spec §3.3]."""
    try:
        dj_profile = DJProfile.objects.get(id=dj_profile_id)
    except DJProfile.DoesNotExist:
        return Response({'error': 'DJ profile not found.'}, status=status.HTTP_404_NOT_FOUND)

    reason = request.data.get('reason', 'Application rejected by admin.')

    dj_profile.status = 'rejected'
    dj_profile.save(update_fields=['status'])

    return Response({
        'status': 'rejected',
        'message': f'{dj_profile.dj_name} application has been rejected.',
        'reason': reason,
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_verify_dj(request, dj_profile_id):
    """Grant Verified DJ badge [Spec P2 §2]."""
    try:
        dj_profile = DJProfile.objects.get(id=dj_profile_id, status='approved')
    except DJProfile.DoesNotExist:
        return Response({'error': 'Approved DJ profile not found.'}, status=status.HTTP_404_NOT_FOUND)

    dj_profile.is_verified_dj = True
    dj_profile.save(update_fields=['is_verified_dj'])

    return Response({
        'status': 'verified',
        'message': f'{dj_profile.dj_name} is now a Verified DJ.',
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_store_pause(request):
    """DJ pauses/unpauses their store [Spec §3.2]."""
    if request.user.role != 'dj':
        return Response({'error': 'Only DJs can access this.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        dj_profile = request.user.profile.dj_profile
    except (Profile.DoesNotExist, DJProfile.DoesNotExist):
        return Response({'error': 'DJ profile not found.'}, status=status.HTTP_404_NOT_FOUND)

    dj_profile.store_paused = not dj_profile.store_paused
    dj_profile.save(update_fields=['store_paused'])

    return Response({
        'store_paused': dj_profile.store_paused,
        'message': 'Store paused.' if dj_profile.store_paused else 'Store resumed.',
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_payout_otp(request):
    """
    DJ requests a 2FA OTP for payout verification [Spec P2 §11, P3 §3.2].
    OTP is sent to the DJ's registered email.
    """
    if request.user.role != 'dj':
        return Response({'error': 'Only DJs can request payout OTPs.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        dj_profile = request.user.profile.dj_profile
    except (Profile.DoesNotExist, DJProfile.DoesNotExist):
        return Response({'error': 'DJ profile not found.'}, status=status.HTTP_404_NOT_FOUND)

    from .payout_auth import generate_payout_otp
    generate_payout_otp(dj_profile)

    return Response({
        'message': 'Verification code sent to your email.',
        'expires_in': '10 minutes'
    })
