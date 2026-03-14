"""
MixMint Mobile API Optimizations.

Lightweight endpoints optimized for mobile apps:
- Minimal payload sizes
- Aggressive caching
- Batch operations
- Offline-first support
"""

from decimal import Decimal
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response


# ============================================
# MOBILE-OPTIMIZED ENDPOINTS
# ============================================

@api_view(['GET'])
@permission_classes([AllowAny])
def mobile_home(request):
    """
    Ultra-light homepage for mobile.
    Returns minimal data, heavily cached.
    """
    cache_key = "mobile_home_v1"
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)
    
    from apps.tracks.models import Track
    
    # Trending (minimal fields)
    trending = Track.objects.filter(
        is_active=True, is_deleted=False
    ).order_by('-download_count').values(
        'id', 'title', 'price', 'cover_image'
    )[:6]
    
    # New releases
    week_ago = timezone.now() - timedelta(days=7)
    new_releases = Track.objects.filter(
        is_active=True, is_deleted=False,
        created_at__gte=week_ago
    ).order_by('-created_at').values(
        'id', 'title', 'price', 'cover_image'
    )[:6]
    
    data = {
        'trending': list(trending),
        'new': list(new_releases),
        'v': 1,  # API version for cache busting
    }
    
    cache.set(cache_key, data, 600)  # 10 min
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def mobile_search(request):
    """
    Fast search for mobile with minimal response.
    """
    import html
    from apps.tracks.models import Track
    
    q = html.escape(request.query_params.get('q', '').strip())
    if not q or len(q) < 2:
        return Response({'results': [], 'total': 0})
    
    # Cache search results
    cache_key = f"msearch_{hash(q)}"
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)
    
    tracks = Track.objects.filter(
        is_active=True, is_deleted=False
    ).filter(
        title__icontains=q
    ).values(
        'id', 'title', 'price', 'cover_image', 'dj__dj_name'
    )[:20]
    
    data = {
        'results': list(tracks),
        'total': len(tracks),
        'q': q,
    }
    
    cache.set(cache_key, data, 300)  # 5 min
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mobile_library(request):
    """
    User's purchased content for offline sync.
    Returns IDs and metadata for offline storage.
    """
    from apps.commerce.models import Purchase
    
    purchases = Purchase.objects.filter(
        user=request.user.profile,
        status='paid'
    ).select_related().values(
        'id', 'content_type', 'content_id', 
        'created_at', 'download_completed'
    ).order_by('-created_at')[:100]
    
    return Response({
        'items': list(purchases),
        'count': len(purchases),
        'sync_time': timezone.now().isoformat(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mobile_dj_stats(request):
    """
    Minimal DJ stats for mobile dashboard.
    """
    if request.user.profile.role != 'dj':
        return Response({'error': 'DJ only'}, status=403)
    
    dj = request.user.profile.dj_profile
    cache_key = f"mdj_stats_{dj.id}"
    
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)
    
    from apps.commerce.models import Purchase, DJWallet
    
    wallet = DJWallet.objects.filter(dj=dj).first()
    today = timezone.now().replace(hour=0, minute=0, second=0)
    
    data = {
        'earnings': str(wallet.total_earnings if wallet else 0),
        'pending': str(wallet.pending_earnings if wallet else 0),
        'sales_today': Purchase.objects.filter(
            seller=dj, status='paid', created_at__gte=today
        ).count(),
        'total_sales': Purchase.objects.filter(seller=dj, status='paid').count(),
    }
    
    cache.set(cache_key, data, 300)
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mobile_notifications(request):
    """
    Unread notifications for mobile.
    Supports pagination via cursor.
    """
    # For now, return empty - can be expanded with notification model
    return Response({
        'notifications': [],
        'unread_count': 0,
        'cursor': None,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_batch(request):
    """
    Batch multiple API calls into one request.
    Reduces round trips for mobile.
    
    Request body:
    {
        "requests": [
            {"id": "1", "endpoint": "home"},
            {"id": "2", "endpoint": "library"},
        ]
    }
    """
    requests_data = request.data.get('requests', [])
    
    if not requests_data or len(requests_data) > 5:
        return Response({'error': 'Max 5 requests per batch'}, status=400)
    
    results = {}
    
    for req in requests_data:
        req_id = req.get('id', '')
        endpoint = req.get('endpoint', '')
        
        if endpoint == 'home':
            # Inline home data
            cache_key = "mobile_home_v1"
            results[req_id] = cache.get(cache_key) or {'trending': [], 'new': []}
        
        elif endpoint == 'library' and request.user.is_authenticated:
            from apps.commerce.models import Purchase
            purchases = Purchase.objects.filter(
                user=request.user.profile, status='paid'
            ).values('id', 'content_type', 'content_id')[:50]
            results[req_id] = {'items': list(purchases)}
        
        elif endpoint == 'dj_stats' and request.user.profile.role == 'dj':
            dj = request.user.profile.dj_profile
            from apps.commerce.models import DJWallet
            wallet = DJWallet.objects.filter(dj=dj).first()
            results[req_id] = {
                'earnings': str(wallet.total_earnings if wallet else 0),
                'pending': str(wallet.pending_earnings if wallet else 0),
            }
        
        else:
            results[req_id] = {'error': 'Unknown endpoint'}
    
    return Response({'results': results})


@api_view(['GET'])
@permission_classes([AllowAny])
def mobile_track_detail(request, track_id):
    """
    Single track detail for mobile.
    Minimal fields, cached.
    """
    cache_key = f"mtrack_{track_id}"
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)
    
    from apps.tracks.models import Track
    
    try:
        track = Track.objects.select_related('dj').get(
            id=track_id, is_active=True, is_deleted=False
        )
    except Track.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    
    data = {
        'id': str(track.id),
        'title': track.title,
        'price': str(track.price),
        'genre': track.genre,
        'cover': track.cover_image.url if track.cover_image else None,
        'preview_url': track.preview_url,
        'dj': {
            'id': str(track.dj.id),
            'name': track.dj.dj_name,
            'verified': track.dj.is_verified,
        },
        'stats': {
            'downloads': track.download_count,
            'rating': str(track.average_rating or 0),
        }
    }
    
    cache.set(cache_key, data, 600)
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mobile_quick_buy(request):
    """
    One-tap purchase for mobile.
    Minimal validation, fast checkout.
    """
    content_type = request.data.get('type')  # 'track' or 'album'
    content_id = request.data.get('id')
    
    if not content_type or not content_id:
        return Response({'error': 'type and id required'}, status=400)
    
    # Get content
    if content_type == 'track':
        from apps.tracks.models import Track
        content = Track.objects.filter(id=content_id, is_active=True).first()
    else:
        from apps.albums.models import AlbumPack
        content = AlbumPack.objects.filter(id=content_id, is_active=True).first()
    
    if not content:
        return Response({'error': 'Not found'}, status=404)
    
    # Check already owned
    from apps.commerce.models import Purchase
    if Purchase.objects.filter(
        user=request.user.profile,
        content_type=content_type,
        content_id=content_id,
        status='paid'
    ).exists():
        return Response({'error': 'Already owned', 'owned': True}, status=400)
    
    # Create purchase
    purchase = Purchase.objects.create(
        user=request.user.profile,
        seller=content.dj,
        content_type=content_type,
        content_id=content_id,
        price_paid=content.price,
        status='pending'
    )
    
    # Get payment URL
    from django.conf import settings
    gateway = settings.ACTIVE_GATEWAY
    
    try:
        result = gateway.create_order(
            amount_paise=int(content.price * 100),
            merchant_transaction_id=str(purchase.id),
            user_id=str(request.user.id),
            redirect_url=f"{settings.BASE_URL}/m/payment/callback"
        )
        purchase.gateway_order_id = result.get('order_id')
        purchase.save()
        
        return Response({
            'purchase_id': str(purchase.id),
            'amount': str(content.price),
            'payment_url': result.get('redirect_url'),
        })
    except Exception as e:
        purchase.delete()
        return Response({'error': 'Payment failed'}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def mobile_genres(request):
    """
    List of genres with counts for mobile filters.
    Cached heavily.
    """
    cache_key = "mobile_genres"
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)
    
    from apps.tracks.models import Track
    from django.db.models import Count
    
    genres = Track.objects.filter(
        is_active=True, is_deleted=False
    ).values('genre').annotate(
        count=Count('id')
    ).order_by('-count')
    
    data = {'genres': list(genres)}
    cache.set(cache_key, data, 3600)  # 1 hour
    return Response(data)
