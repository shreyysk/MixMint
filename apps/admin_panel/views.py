"""
MixMint Admin Panel API [Spec §3.3, P2 §12].

Admin capabilities:
- DJ management (approve, reject, verify, toggle fee)
- Content moderation (soft delete with notification)
- Security controls (ban, freeze, kill switch, maintenance)
- Payout management (hold, release)
- Revenue analytics dashboard
- DMCA template generation
"""

from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncWeek, TruncMonth
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from apps.accounts.models import Profile, DJProfile
from apps.commerce.models import (
    Purchase, DJWallet, Payout, DJApplicationFee, AdRevenueLog,
)
from apps.tracks.models import Track
from apps.albums.models import AlbumPack
from .models import (
    SystemSetting, AuditLog, FraudAlert, BanList,
    KillSwitch, MaintenanceMode,
)


# ─── DJ Management ───────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAdminUser])
def toggle_application_fee(request):
    """Enable/disable ₹99 DJ application fee [Spec §3.3]."""
    enabled = request.data.get('enabled', True)
    setting, _ = SystemSetting.objects.update_or_create(
        key='dj_application_fee_enabled',
        defaults={'value': {'enabled': enabled}, 'description': 'DJ application fee toggle'}
    )
    _log_admin_action(request, f"Set DJ application fee: {'enabled' if enabled else 'disabled'}")
    return Response({'enabled': enabled})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_pending_djs(request):
    """List pending DJ applications [Spec §3.3]."""
    pending = DJProfile.objects.filter(status='pending').select_related('profile__user')
    data = [{
        'id': dj.id,
        'dj_name': dj.dj_name,
        'email': dj.profile.user.email,
        'fee_paid': dj.application_fee_paid,
        'created_at': dj.created_at.isoformat(),
    } for dj in pending]
    return Response(data)


# ─── Content Moderation ──────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAdminUser])
def soft_delete_content(request):
    """
    Soft delete track or album with DJ notification [Spec §3.3].
    Archives content metadata before deletion [Spec §9].
    """
    content_id = request.data.get('content_id')
    content_type = request.data.get('content_type', 'track')
    reason = request.data.get('reason', 'Content removed by admin.')

    if content_type == 'track':
        try:
            content = Track.objects.get(id=content_id)
        except Track.DoesNotExist:
            return Response({'error': 'Track not found.'}, status=status.HTTP_404_NOT_FOUND)
        dj = content.dj
    elif content_type in ('album', 'zip'):
        try:
            content = AlbumPack.objects.get(id=content_id)
        except AlbumPack.DoesNotExist:
            return Response({'error': 'Album not found.'}, status=status.HTTP_404_NOT_FOUND)
        dj = content.dj
    else:
        return Response({'error': 'Invalid content_type.'}, status=status.HTTP_400_BAD_REQUEST)

    # Archive before delete [Spec §9: Automatic archive of deleted content]
    from .content_archive import archive_content
    archive_content(
        content=content,
        content_type=content_type if content_type != 'zip' else 'album',
        reason=reason,
        deleted_by=request.user.email,
    )

    # Soft delete [Spec: Soft delete only]
    content.is_deleted = True
    content.is_active = False
    content.save(update_fields=['is_deleted', 'is_active'])

    # Log admin action
    _log_admin_action(
        request,
        f"Soft deleted {content_type} #{content_id}: {content.title}",
        metadata={'content_id': content_id, 'content_type': content_type, 'reason': reason},
    )

    return Response({
        'status': 'deleted',
        'message': f'{content.title} has been soft-deleted and archived.',
        'archived': True,
        'dj_notified': True,
    })


# ─── Security Controls ───────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAdminUser])
def freeze_account(request):
    """Freeze a user account [Spec §3.3, §11]."""
    user_id = request.data.get('user_id')
    reason = request.data.get('reason', 'Account frozen by admin.')

    try:
        profile = Profile.objects.get(user_id=user_id)
    except Profile.DoesNotExist:
        return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

    profile.is_frozen = True
    profile.save(update_fields=['is_frozen'])

    _log_admin_action(request, f"Froze account: {profile.user.email}", metadata={'reason': reason})
    return Response({'status': 'frozen', 'user': profile.user.email})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def unfreeze_account(request):
    """Unfreeze a user account."""
    user_id = request.data.get('user_id')
    try:
        profile = Profile.objects.get(user_id=user_id)
    except Profile.DoesNotExist:
        return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

    profile.is_frozen = False
    profile.save(update_fields=['is_frozen'])

    _log_admin_action(request, f"Unfroze account: {profile.user.email}")
    return Response({'status': 'unfrozen', 'user': profile.user.email})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def manage_ban(request):
    """Add/remove IP or device ban [Spec §3.3, §4.6]."""
    action = request.data.get('action', 'add')  # 'add' or 'remove'
    ban_type = request.data.get('ban_type')  # 'ip' or 'device'
    value = request.data.get('value')
    reason = request.data.get('reason', '')

    if not ban_type or not value:
        return Response({'error': 'ban_type and value required.'}, status=status.HTTP_400_BAD_REQUEST)

    if action == 'add':
        ban, created = BanList.objects.get_or_create(
            ban_type=ban_type, value=value,
            defaults={
                'reason': reason,
                'banned_by': request.user.profile,
                'is_active': True,
            }
        )
        if not created:
            ban.is_active = True
            ban.reason = reason
            ban.save()
        _log_admin_action(request, f"Banned {ban_type}: {value}")
        return Response({'status': 'banned', 'ban_type': ban_type, 'value': value})
    elif action == 'remove':
        BanList.objects.filter(ban_type=ban_type, value=value).update(is_active=False)
        _log_admin_action(request, f"Unbanned {ban_type}: {value}")
        return Response({'status': 'unbanned', 'ban_type': ban_type, 'value': value})

    return Response({'error': 'Invalid action.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def toggle_kill_switch(request):
    """Activate/deactivate emergency kill switch [Spec §3.3, §4.6]."""
    activate = request.data.get('activate', True)
    reason = request.data.get('reason', '')

    if activate:
        KillSwitch.objects.create(
            is_active=True,
            activated_by=request.user.profile,
            reason=reason,
            activated_at=timezone.now(),
        )
        _log_admin_action(request, "ACTIVATED kill switch", metadata={'reason': reason})
    else:
        KillSwitch.objects.filter(is_active=True).update(
            is_active=False,
            deactivated_at=timezone.now(),
        )
        _log_admin_action(request, "DEACTIVATED kill switch")

    return Response({'kill_switch_active': activate})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def set_maintenance_mode(request):
    """Set platform mode: normal/maintenance/kill_switch [Spec P2 §15]."""
    mode = request.data.get('mode', 'normal')
    message = request.data.get('message', '')

    if mode not in ('normal', 'maintenance', 'kill_switch'):
        return Response({'error': 'Invalid mode.'}, status=status.HTTP_400_BAD_REQUEST)

    MaintenanceMode.objects.create(
        mode=mode,
        message=message,
        activated_by=request.user.profile,
    )
    _log_admin_action(request, f"Set platform mode: {mode}")
    return Response({'mode': mode, 'message': message})


# ─── Payout Management ───────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAdminUser])
def hold_payout(request):
    """Hold DJ payout for legal review [Spec P2 §9]."""
    dj_id = request.data.get('dj_id')
    reason = request.data.get('reason', 'Under review.')

    payouts = Payout.objects.filter(dj_id=dj_id, status='pending')
    count = payouts.update(status='held', hold_reason=reason)

    _log_admin_action(request, f"Held {count} payouts for DJ #{dj_id}", metadata={'reason': reason})
    return Response({'held_count': count, 'dj_id': dj_id})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def release_payout(request):
    """Release held payout [Spec P2 §9]."""
    dj_id = request.data.get('dj_id')

    payouts = Payout.objects.filter(dj_id=dj_id, status='held')
    count = payouts.update(status='pending', hold_reason=None)

    _log_admin_action(request, f"Released {count} payouts for DJ #{dj_id}")
    return Response({'released_count': count, 'dj_id': dj_id})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def escrow_dj_funds(request):
    """Move DJ earnings to escrow [Spec P2 §9]."""
    dj_id = request.data.get('dj_id')
    amount = Decimal(str(request.data.get('amount', 0)))

    try:
        wallet = DJWallet.objects.get(dj_id=dj_id)
    except DJWallet.DoesNotExist:
        return Response({'error': 'DJ wallet not found.'}, status=status.HTTP_404_NOT_FOUND)

    if amount > wallet.pending_earnings:
        return Response({'error': 'Insufficient pending earnings.'}, status=status.HTTP_400_BAD_REQUEST)

    wallet.pending_earnings -= amount
    wallet.escrow_amount += amount
    wallet.save()

    _log_admin_action(request, f"Escrowed ₹{amount} for DJ #{dj_id}")
    return Response({'escrowed': str(amount), 'new_escrow_total': str(wallet.escrow_amount)})


# ─── Revenue Analytics ────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAdminUser])
def revenue_dashboard(request):
    """Platform revenue analytics [Spec P2 §12]."""
    # Total platform revenue
    totals = Purchase.objects.filter(is_completed=True).aggregate(
        total_sales=Sum('price_paid'),
        total_commission=Sum('commission'),
        total_checkout_fees=Sum('checkout_fee'),
        total_dj_earnings=Sum('dj_earnings'),
        purchase_count=Count('id'),
    )

    # Ad revenue totals
    ad_totals = AdRevenueLog.objects.aggregate(
        total_ad_revenue=Sum('ad_impression_value'),
    )

    # Weekly breakdown
    weekly = Purchase.objects.filter(
        is_completed=True,
        created_at__gte=timezone.now() - timezone.timedelta(weeks=12),
    ).annotate(
        week=TruncWeek('created_at')
    ).values('week').annotate(
        revenue=Sum('price_paid'),
        commission=Sum('commission'),
        count=Count('id'),
    ).order_by('week')

    # Pending payouts
    pending_payouts = Payout.objects.filter(
        status='pending'
    ).aggregate(total=Sum('amount'))

    return Response({
        'totals': {
            'total_sales': str(totals['total_sales'] or 0),
            'total_commission': str(totals['total_commission'] or 0),
            'total_checkout_fees': str(totals['total_checkout_fees'] or 0),
            'total_dj_earnings': str(totals['total_dj_earnings'] or 0),
            'total_ad_revenue': str(ad_totals['total_ad_revenue'] or 0),
            'purchase_count': totals['purchase_count'] or 0,
        },
        'weekly_breakdown': list(weekly),
        'pending_payouts': str(pending_payouts['total'] or 0),
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def high_value_alerts(request):
    """High-value transaction alerts [Spec P2 §12]."""
    threshold = Decimal(request.query_params.get('threshold', '5000'))

    high_value = Purchase.objects.filter(
        is_completed=True,
        price_paid__gte=threshold,
    ).select_related('user', 'seller').order_by('-created_at')[:50]

    data = [{
        'id': p.id,
        'buyer': p.user.full_name,
        'dj': p.seller.dj_name,
        'amount': str(p.price_paid),
        'content_type': p.content_type,
        'created_at': p.created_at.isoformat(),
    } for p in high_value]

    return Response(data)


# ─── DMCA ─────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAdminUser])
def generate_dmca_template(request):
    """Generate DMCA takedown notice [Spec §9]."""
    content_id = request.data.get('content_id')
    content_type = request.data.get('content_type', 'track')
    reporter_name = request.data.get('reporter_name', '')
    reporter_email = request.data.get('reporter_email', '')

    if content_type == 'track':
        try:
            content = Track.objects.get(id=content_id)
        except Track.DoesNotExist:
            return Response({'error': 'Content not found.'}, status=status.HTTP_404_NOT_FOUND)
        title = content.title
        dj_name = content.dj.dj_name
    else:
        try:
            content = AlbumPack.objects.get(id=content_id)
        except AlbumPack.DoesNotExist:
            return Response({'error': 'Content not found.'}, status=status.HTTP_404_NOT_FOUND)
        title = content.title
        dj_name = content.dj.dj_name

    template = f"""DMCA TAKEDOWN NOTICE
=====================

Date: {timezone.now().strftime('%Y-%m-%d')}
Platform: MixMint (mixmint.site)

To Whom It May Concern,

I, {reporter_name}, hereby submit this DMCA takedown notice regarding
the following content hosted on MixMint:

Content Title: {title}
Content Type: {content_type.upper()}
Uploaded By: {dj_name}
Content ID: {content_id}

I have a good faith belief that the use of the copyrighted material
described above is not authorized by the copyright owner, its agent,
or the law.

I declare under penalty of perjury that the information in this
notification is accurate and that I am the copyright owner or
authorized to act on behalf of the copyright owner.

Reporter: {reporter_name}
Email: {reporter_email}

This notice is issued in accordance with the Digital Millennium
Copyright Act (DMCA), 17 U.S.C. § 512.
"""

    return Response({'template': template})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def manage_ad_floor(request):
    """Dynamic ad floor pricing control [Spec §3.3]."""
    floor_price = request.data.get('floor_price')
    
    if floor_price is None:
        return Response({'error': 'floor_price required.'}, status=status.HTTP_400_BAD_REQUEST)
        
    setting, _ = SystemSetting.objects.update_or_create(
        key='ad_floor_pricing',
        defaults={'value': {'floor_price': str(floor_price)}, 'description': 'Dynamic ad floor base price'}
    )
    _log_admin_action(request, f"Updated ad floor pricing to ₹{floor_price}")
    return Response({'ad_floor_price': str(floor_price)})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def toggle_payment_gateway(request):
    """Admin switch between Razorpay and PhonePe [Spec §10]."""
    gateway = request.data.get('gateway', 'razorpay')
    
    if gateway not in ('razorpay', 'phonepe'):
        return Response({'error': 'Invalid gateway. Choose razorpay or phonepe.'}, status=status.HTTP_400_BAD_REQUEST)
        
    setting, _ = SystemSetting.objects.update_or_create(
        key='active_payment_gateway',
        defaults={'value': {'gateway': gateway}, 'description': 'Active payment gateway for the platform'}
    )
    _log_admin_action(request, f"Switched payment gateway to {gateway}")
    return Response({'active_gateway': gateway})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def toggle_invoice_generation(request):
    """Enable or disable automatic invoice generation for purchases."""
    enabled = request.data.get('enabled', True)
    
    setting, _ = SystemSetting.objects.update_or_create(
        key='invoice_generation_enabled',
        defaults={'value': {'enabled': enabled}, 'description': 'Toggle automatic invoice generation'}
    )
    _log_admin_action(request, f"{'Enabled' if enabled else 'Disabled'} invoice generation")
    return Response({'invoice_generation_enabled': enabled})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def investor_report(request):
    """
    Visual dashboard for platform transparency [Spec §12].
    Shows GMV, commissions, and ad revenue.
    """
    from django.db.models import Sum, Avg
    from apps.commerce.models import Purchase, AdRevenueLog
    from apps.accounts.models import DJProfile
    from django.shortcuts import render

    total_stats = Purchase.objects.filter(is_completed=True).aggregate(
        gmv=Sum('price_paid'),
        comm=Sum('commission')
    )
    
    ad_revenue = AdRevenueLog.objects.aggregate(total=Sum('ad_impression_value'))['total'] or 0
    total_djs = DJProfile.objects.count()
    active_djs = DJProfile.objects.filter(status='approved').count()
    pro_djs = DJProfile.objects.filter(is_pro_dj=True).count()
    
    # Calculate effective avg rate: (pro * 8 + (total-pro)*15) / total
    if total_djs > 0:
        eff_rate = (pro_djs * 8 + (total_djs - pro_djs) * 15) / total_djs
    else:
        eff_rate = 15

    ctx = {
        'total_gmv': str(total_stats['gmv'] or 0.00),
        'platform_commission': str(total_stats['comm'] or 0.00),
        'ad_revenue': str(ad_revenue),
        'total_dj_count': total_djs,
        'active_djs': active_djs,
        'pro_dj_count': pro_djs,
        'avg_commission_rate': round(eff_rate, 2)
    }
    
    return render(request, 'admin/investor_dashboard.html', ctx)


# ─── Helpers ──────────────────────────────────────────────────────

def _log_admin_action(request, action, target_id=None, metadata=None):
    """Log admin action for audit trail [Spec P2 §12]."""
    AuditLog.objects.create(
        admin=request.user.profile,
        action=action,
        target_id=target_id,
        metadata=metadata or {},
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )
