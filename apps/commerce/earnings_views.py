"""
MixMint DJ Earnings Analytics API [Spec §3.2 — Revenue Only Analytics].

Provides:
- Lifetime, weekly, monthly earnings
- Earnings per track
- Earnings per album
- Pending payout
- Paid payouts history
- Ad revenue breakdown

No engagement metrics. No demographic data. Revenue only.
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, Count
from django.db.models.functions import TruncWeek
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.accounts.models import DJProfile
from apps.commerce.models import Purchase, Payout, AdRevenueLog
from apps.tracks.models import Track
from apps.albums.models import AlbumPack


def _get_dj_profile(request):
    """Helper to get the authenticated DJ's profile or raise 403."""
    profile = request.user.profile
    if profile.role != 'dj':
        return None, Response(
            {'error': 'Only DJs can access earnings analytics.'},
            status=status.HTTP_403_FORBIDDEN
        )
    try:
        dj_profile = profile.dj_profile
        if dj_profile.status != 'approved':
            return None, Response(
                {'error': 'Your DJ application is not yet approved.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return dj_profile, None
    except DJProfile.DoesNotExist:
        return None, Response({'error': 'DJ profile not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dj_earnings_overview(request):
    """
    Full DJ earnings overview dashboard [Spec §3.2].
    Lifetime, weekly, monthly earnings + wallet state.
    """
    dj, err = _get_dj_profile(request)
    if err:
        return err

    now = timezone.now()
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    # Sales earnings
    lifetime = Purchase.objects.filter(
        seller=dj, status='paid'
    ).aggregate(
        total_dj_earnings=Sum('dj_earnings'),
        total_sales=Sum('price_paid'),
        sale_count=Count('id'),
    )

    weekly = Purchase.objects.filter(
        seller=dj, status='paid', created_at__gte=week_start
    ).aggregate(earnings=Sum('dj_earnings'), count=Count('id'))

    monthly = Purchase.objects.filter(
        seller=dj, status='paid', created_at__gte=month_start
    ).aggregate(earnings=Sum('dj_earnings'), count=Count('id'))

    # Ad revenue
    ad_lifetime = AdRevenueLog.objects.filter(dj=dj).aggregate(
        total=Sum('ad_impression_value')
    )
    ad_weekly = AdRevenueLog.objects.filter(
        dj=dj, created_at__gte=week_start
    ).aggregate(total=Sum('ad_impression_value'))

    # Wallet state
    try:
        wallet = dj.wallet
        wallet_data = {
            'total_earnings': str(wallet.total_earnings),
            'pending_earnings': str(wallet.pending_earnings),
            'escrow_amount': str(wallet.escrow_amount),
            'available_for_payout': str(wallet.available_for_payout),
        }
    except Exception:
        wallet_data = {
            'total_earnings': '0.00',
            'pending_earnings': '0.00',
            'escrow_amount': '0.00',
            'available_for_payout': '0.00',
        }

    # Pending payout
    pending_payout = Payout.objects.filter(
        dj=dj, status='pending'
    ).aggregate(total=Sum('amount'))

    return Response({
        'lifetime': {
            'dj_earnings': str(lifetime['total_dj_earnings'] or 0),
            'total_sales_volume': str(lifetime['total_sales'] or 0),
            'sale_count': lifetime['sale_count'] or 0,
        },
        'weekly': {
            'earnings': str(weekly['earnings'] or 0),
            'sale_count': weekly['count'] or 0,
        },
        'monthly': {
            'earnings': str(monthly['earnings'] or 0),
            'sale_count': monthly['count'] or 0,
        },
        'ad_revenue': {
            'lifetime': str(ad_lifetime['total'] or 0),
            'this_week': str(ad_weekly['total'] or 0),
        },
        'wallet': wallet_data,
        'pending_payout': str(pending_payout['total'] or 0),
        'commission_rate': '8%' if request.user.profile.is_pro_dj else '15%',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def earnings_by_track(request):
    """
    Earnings breakdown per track [Spec §3.2].
    Sorted by highest earner.
    """
    dj, err = _get_dj_profile(request)
    if err:
        return err

    tracks = Track.objects.filter(dj=dj, is_deleted=False)

    data = []
    for track in tracks:
        purchases = Purchase.objects.filter(
            seller=dj, content_type='track', content_id=track.id, status='paid'
        ).aggregate(
            earnings=Sum('dj_earnings'),
            sales=Count('id'),
            revenue=Sum('price_paid'),
        )
        data.append({
            'track_id': track.id,
            'title': track.title,
            'genre': track.genre,
            'price': str(track.price),
            'download_count': track.download_count,
            'earnings': str(purchases['earnings'] or 0),
            'sale_count': purchases['sales'] or 0,
            'gross_revenue': str(purchases['revenue'] or 0),
            'is_active': track.is_active,
        })

    # Sort by earnings descending
    data.sort(key=lambda x: Decimal(x['earnings']), reverse=True)
    return Response({'tracks': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def earnings_by_album(request):
    """
    Earnings breakdown per album [Spec §3.2].
    """
    dj, err = _get_dj_profile(request)
    if err:
        return err

    albums = AlbumPack.objects.filter(dj=dj, is_deleted=False)

    data = []
    for album in albums:
        purchases = Purchase.objects.filter(
            seller=dj, content_type='album', content_id=album.id, status='paid'
        ).aggregate(
            earnings=Sum('dj_earnings'),
            sales=Count('id'),
            revenue=Sum('price_paid'),
        )
        data.append({
            'album_id': album.id,
            'title': album.title,
            'price': str(album.price),
            'earnings': str(purchases['earnings'] or 0),
            'sale_count': purchases['sales'] or 0,
            'gross_revenue': str(purchases['revenue'] or 0),
            'is_active': album.is_active,
        })

    data.sort(key=lambda x: Decimal(x['earnings']), reverse=True)
    return Response({'albums': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def weekly_earnings_chart(request):
    """
    Weekly earnings for the last 12 weeks [Spec §3.2].
    For charting on the DJ dashboard.
    """
    dj, err = _get_dj_profile(request)
    if err:
        return err

    twelve_weeks_ago = timezone.now() - timedelta(weeks=12)

    weekly = Purchase.objects.filter(
        seller=dj, status='paid', created_at__gte=twelve_weeks_ago
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payout_history(request):
    """
    Paid payouts history for the DJ [Spec §3.2].
    """
    dj, err = _get_dj_profile(request)
    if err:
        return err

    payouts = Payout.objects.filter(dj=dj).order_by('-created_at')[:50]

    return Response({
        'payouts': [{
            'id': p.id,
            'amount': str(p.amount),
            'status': p.status,
            'payment_reference': p.payment_reference,
            'created_at': p.created_at.isoformat(),
            'processed_at': p.processed_at.isoformat() if p.processed_at else None,
        } for p in payouts]
    })
