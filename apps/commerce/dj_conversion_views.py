"""
DJ Conversion API Endpoints [High Conversion Enhancement].

Endpoints for:
- Referral code generation and tracking
- Promo code application
- Milestone progress
- Onboarding status
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
import secrets

from .dj_conversion import (
    DJReferralProgram, DJMilestoneReward, DJPromoCode,
    DJOnboardingProgress, DJWelcomeBonus
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_referral_code(request):
    """
    Get or generate DJ's unique referral code.
    DJs earn ₹100 when their referral makes first sale.
    """
    if request.user.profile.role != 'dj':
        return Response({'error': 'Only DJs can access referral codes.'}, status=403)
    
    dj_profile = request.user.profile.dj_profile
    
    # Check for existing ambassador code
    from apps.accounts.models import AmbassadorCode
    code, created = AmbassadorCode.objects.get_or_create(
        dj=dj_profile,
        defaults={'code': f"DJ{secrets.token_hex(4).upper()}"}
    )
    
    # Get referral stats
    referrals = DJReferralProgram.objects.filter(referrer=dj_profile)
    
    return Response({
        'referral_code': code.code,
        'referral_url': f"https://mixmint.in/join?ref={code.code}",
        'stats': {
            'total_referrals': referrals.count(),
            'successful_referrals': referrals.filter(first_sale_achieved=True).count(),
            'pending_referrals': referrals.filter(first_sale_achieved=False).count(),
            'total_earned': sum(r.referrer_bonus for r in referrals.filter(referrer_paid=True)),
        },
        'rewards': {
            'referrer_bonus': '₹100 when your referral makes their first sale',
            'referred_bonus': '₹50 bonus for the new DJ',
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_referral_code(request):
    """
    Apply a referral code when signing up as DJ.
    Called during DJ application process.
    """
    code = request.data.get('referral_code', '').strip().upper()
    if not code:
        return Response({'error': 'Referral code is required.'}, status=400)
    
    if request.user.profile.role != 'dj':
        return Response({'error': 'Only DJs can apply referral codes.'}, status=403)
    
    dj_profile = request.user.profile.dj_profile
    
    # Check if already referred
    if DJReferralProgram.objects.filter(referred=dj_profile).exists():
        return Response({'error': 'You have already used a referral code.'}, status=400)
    
    # Find referrer
    from apps.accounts.models import AmbassadorCode
    try:
        referrer_code = AmbassadorCode.objects.get(code=code)
    except AmbassadorCode.DoesNotExist:
        return Response({'error': 'Invalid referral code.'}, status=404)
    
    # Can't refer yourself
    if referrer_code.dj == dj_profile:
        return Response({'error': 'You cannot use your own referral code.'}, status=400)
    
    # Create referral relationship
    DJReferralProgram.objects.create(
        referrer=referrer_code.dj,
        referred=dj_profile,
        referral_code=code
    )
    
    return Response({
        'status': 'success',
        'message': 'Referral code applied! You\'ll receive ₹50 bonus after your first sale.',
        'referrer': referrer_code.dj.dj_name
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_promo_code(request):
    """Apply a promotional code for commission discount."""
    code = request.data.get('promo_code', '').strip().upper()
    if not code:
        return Response({'error': 'Promo code is required.'}, status=400)
    
    if request.user.profile.role != 'dj':
        return Response({'error': 'Only DJs can apply promo codes.'}, status=403)
    
    dj_profile = request.user.profile.dj_profile
    
    try:
        promo = DJPromoCode.objects.get(code=code)
    except DJPromoCode.DoesNotExist:
        return Response({'error': 'Invalid promo code.'}, status=404)
    
    success, message = promo.apply_to_dj(dj_profile)
    
    if success:
        return Response({'status': 'success', 'message': message})
    return Response({'error': message}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_milestones(request):
    """Get DJ's milestone progress and rewards."""
    if request.user.profile.role != 'dj':
        return Response({'error': 'Only DJs can view milestones.'}, status=403)
    
    dj_profile = request.user.profile.dj_profile
    
    # Check for new milestones
    newly_awarded = DJMilestoneReward.check_and_award(dj_profile)
    
    # Get all milestones
    achieved = DJMilestoneReward.objects.filter(dj=dj_profile)
    achieved_list = [m.milestone for m in achieved]
    
    milestones = []
    for key, display in DJMilestoneReward.MILESTONES:
        milestones.append({
            'id': key,
            'name': display,
            'reward': f"₹{DJMilestoneReward.REWARDS[key]}",
            'achieved': key in achieved_list,
            'newly_achieved': key in newly_awarded,
        })
    
    total_earned = sum(m.reward_amount for m in achieved.filter(credited=True))
    
    return Response({
        'milestones': milestones,
        'total_milestone_rewards': f"₹{total_earned}",
        'newly_awarded': newly_awarded,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_onboarding_status(request):
    """Get DJ onboarding progress."""
    if request.user.profile.role != 'dj':
        return Response({'error': 'Only DJs can view onboarding status.'}, status=403)
    
    dj_profile = request.user.profile.dj_profile
    
    progress, _ = DJOnboardingProgress.objects.get_or_create(dj=dj_profile)
    
    # Auto-detect completed steps
    progress.profile_completed = bool(dj_profile.bio and dj_profile.profile_image)
    progress.first_track_uploaded = dj_profile.tracks.filter(is_deleted=False).exists()
    progress.store_customized = bool(dj_profile.banner_image or dj_profile.tagline)
    
    # Check bank details
    from apps.accounts.models import BankAccount
    progress.bank_details_added = BankAccount.objects.filter(dj=dj_profile, is_verified=True).exists()
    
    # Check if any track has custom price
    progress.pricing_set = dj_profile.tracks.filter(is_deleted=False).exclude(price=29).exists()
    
    completion = progress.update_progress()
    
    steps = [
        {'id': 'profile', 'name': 'Complete your profile', 'completed': progress.profile_completed,
         'tip': 'Add a bio and profile photo to build trust with buyers'},
        {'id': 'bank', 'name': 'Add bank details', 'completed': progress.bank_details_added,
         'tip': 'Required to receive your earnings'},
        {'id': 'track', 'name': 'Upload your first track', 'completed': progress.first_track_uploaded,
         'tip': 'Get ₹50 welcome bonus after uploading!'},
        {'id': 'pricing', 'name': 'Set custom pricing', 'completed': progress.pricing_set,
         'tip': 'Price your tracks based on their value'},
        {'id': 'store', 'name': 'Customize your store', 'completed': progress.store_customized,
         'tip': 'Add a banner and tagline to stand out'},
    ]
    
    return Response({
        'completion_percent': completion,
        'steps': steps,
        'welcome_bonus_available': not progress.first_track_uploaded,
        'estimated_time': '10 minutes' if completion < 100 else None,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dj_dashboard_stats(request):
    """
    Enhanced DJ dashboard with conversion-focused metrics.
    Shows earnings, milestones, and growth opportunities.
    """
    if request.user.profile.role != 'dj':
        return Response({'error': 'Only DJs can access this.'}, status=403)
    
    dj_profile = request.user.profile.dj_profile
    
    from apps.commerce.models import Purchase, DJWallet
    from apps.commerce.analytics import get_dj_monthly_earnings, calculate_earnings_forecast
    
    # Basic stats
    wallet = DJWallet.objects.filter(dj=dj_profile).first()
    total_earnings = wallet.total_earnings if wallet else 0
    pending_earnings = wallet.pending_earnings if wallet else 0
    
    # Sales stats
    total_sales = Purchase.objects.filter(seller=dj_profile, status='paid').count()
    this_month_sales = Purchase.objects.filter(
        seller=dj_profile, status='paid',
        created_at__month=timezone.now().month,
        created_at__year=timezone.now().year
    ).count()
    
    # Forecast
    try:
        forecast = calculate_earnings_forecast(dj_profile.id)
    except Exception:
        forecast = None
    
    # Milestones
    achieved_milestones = DJMilestoneReward.objects.filter(dj=dj_profile).count()
    
    # Next milestone hint
    next_milestone = None
    if total_sales < 10:
        next_milestone = {'target': '10 sales', 'reward': '₹100', 'progress': f'{total_sales}/10'}
    elif total_sales < 50:
        next_milestone = {'target': '50 sales', 'reward': '₹250', 'progress': f'{total_sales}/50'}
    
    # Referral stats
    referral_earnings = DJReferralProgram.objects.filter(
        referrer=dj_profile, referrer_paid=True
    ).count() * 100
    
    return Response({
        'earnings': {
            'total': f"₹{total_earnings}",
            'pending': f"₹{pending_earnings}",
            'this_month': f"₹{get_dj_monthly_earnings(dj_profile.id)}",
        },
        'sales': {
            'total': total_sales,
            'this_month': this_month_sales,
        },
        'forecast': forecast,
        'milestones': {
            'achieved': achieved_milestones,
            'total': len(DJMilestoneReward.MILESTONES),
            'next': next_milestone,
        },
        'referrals': {
            'total_earned': f"₹{referral_earnings}",
        },
        'tips': [
            'Share your tracks on social media to boost sales',
            'Invite other DJs using your referral code to earn ₹100 per referral',
            'Upload consistently to build your audience',
        ]
    })
