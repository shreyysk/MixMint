"""
MixMint DJ Analytics API [Spec §3.2].

Revenue-only analytics for DJs:
- Lifetime earnings
- Weekly earnings
- Monthly earnings
- Earnings per track
- Earnings per album
- Pending payout
- Paid payouts history

No engagement metrics. No demographic data.
"""

from datetime import timedelta

from django.db.models import Sum, Count
from django.db.models.functions import TruncWeek
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.commerce.models import Purchase, Payout, AdRevenueLog


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dj_earnings_overview(request):
    """
    DJ earnings dashboard overview [Spec §3.2].
    Returns lifetime, weekly, monthly earnings + pending payout.
    """
    if request.user.profile.role != 'dj':
        return Response({'error': 'DJ access only.'}, status=403)

    try:
        dj_profile = request.user.profile.dj_profile
        wallet = dj_profile.wallet
    except Exception:
        return Response({'error': 'DJ profile or wallet not found.'}, status=404)

    now = timezone.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    from apps.commerce.analytics import get_dj_monthly_earnings, get_dj_lifetime_earnings
    
    # Lifetime earnings [Spec §3.2]
    lifetime_total = get_dj_lifetime_earnings(dj_profile.id)

    # Weekly earnings (kept real-time for now as per Fix 11 NEAR-REAL-TIME requirement, but monthly/lifetime are cached)
    weekly = Purchase.objects.filter(
        seller=dj_profile, is_completed=True, download_completed=True,
        created_at__gte=week_ago,
    ).aggregate(total=Sum('dj_earnings'))

    # Monthly earnings (cached 5 min)
    monthly_total = get_dj_monthly_earnings(dj_profile.id)

    # Ad revenue
    ad_lifetime = AdRevenueLog.objects.filter(dj=dj_profile).aggregate(total=Sum('ad_impression_value'))
    ad_weekly = AdRevenueLog.objects.filter(dj=dj_profile, created_at__gte=week_ago).aggregate(total=Sum('ad_impression_value'))

    return Response({
        'lifetime_earnings': str(lifetime_total),
        'weekly_earnings': str(weekly['total'] or 0),
        'monthly_earnings': str(monthly_total),
        'pending_payout': str(wallet.pending_earnings),
        'escrow_amount': str(wallet.escrow_amount),
        'available_for_payout': str(wallet.available_for_payout),
        'total_earnings': str(wallet.total_earnings),
        'ad_revenue_lifetime': str(ad_lifetime['total'] or 0),
        'ad_revenue_this_week': str(ad_weekly['total'] or 0),
        'commission_rate': '8%' if request.user.profile.is_pro_dj else '15%',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dj_earnings_per_track(request):
    """Earnings breakdown per track [Spec §3.2]."""
    if request.user.profile.role != 'dj':
        return Response({'error': 'DJ access only.'}, status=403)

    dj_profile = request.user.profile.dj_profile

    track_earnings = Purchase.objects.filter(
        seller=dj_profile, content_type='track',
        is_completed=True, download_completed=True,
    ).values('content_id').annotate(
        total_earned=Sum('dj_earnings'),
        sale_count=Count('id'),
    ).order_by('-total_earned')

    # Enrich with track titles
    from apps.tracks.models import Track
    results = []
    for entry in track_earnings:
        try:
            track = Track.objects.get(id=entry['content_id'])
            results.append({
                'track_id': entry['content_id'],
                'title': track.title,
                'total_earned': str(entry['total_earned']),
                'sale_count': entry['sale_count'],
                'price': str(track.price),
            })
        except Track.DoesNotExist:
            continue

    return Response({'tracks': results})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dj_earnings_per_album(request):
    """Earnings breakdown per album [Spec §3.2]."""
    if request.user.profile.role != 'dj':
        return Response({'error': 'DJ access only.'}, status=403)

    dj_profile = request.user.profile.dj_profile

    album_earnings = Purchase.objects.filter(
        seller=dj_profile, content_type='album',
        is_completed=True, download_completed=True,
    ).values('content_id').annotate(
        total_earned=Sum('dj_earnings'),
        sale_count=Count('id'),
    ).order_by('-total_earned')

    from apps.albums.models import AlbumPack
    results = []
    for entry in album_earnings:
        try:
            album = AlbumPack.objects.get(id=entry['content_id'])
            results.append({
                'album_id': entry['content_id'],
                'title': album.title,
                'total_earned': str(entry['total_earned']),
                'sale_count': entry['sale_count'],
                'price': str(album.price),
            })
        except AlbumPack.DoesNotExist:
            continue

    return Response({'albums': results})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dj_payout_history(request):
    """Paid payouts history [Spec §3.2]."""
    if request.user.profile.role != 'dj':
        return Response({'error': 'DJ access only.'}, status=403)

    dj_profile = request.user.profile.dj_profile

    payouts = Payout.objects.filter(dj=dj_profile).order_by('-created_at')

    data = [{
        'id': p.id,
        'amount': str(p.amount),
        'status': p.status,
        'created_at': p.created_at.isoformat(),
        'processed_at': p.processed_at.isoformat() if p.processed_at else None,
    } for p in payouts]

    return Response({'payouts': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dj_weekly_chart(request):
    """Weekly earnings for the last 12 weeks for charting [Spec §3.2]."""
    if request.user.profile.role != 'dj':
        return Response({'error': 'DJ access only.'}, status=403)

    dj_profile = request.user.profile.dj_profile
    twelve_weeks_ago = timezone.now() - timedelta(weeks=12)

    weekly = Purchase.objects.filter(
        seller=dj_profile, is_completed=True, download_completed=True,
        created_at__gte=twelve_weeks_ago,
    ).annotate(week=TruncWeek('created_at')).values('week').annotate(
        earnings=Sum('dj_earnings'),
        sales=Count('id'),
    ).order_by('week')

    return Response({
        'chart_data': [{
            'week': w['week'].isoformat(),
            'earnings': str(w['earnings'] or 0),
            'sales': w['sales'],
        } for w in weekly]
    })
