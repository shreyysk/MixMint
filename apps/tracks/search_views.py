"""
MixMint Advanced Search & Discovery [Spec §8].

Supports:
- DJ name search (partial spelling)
- Track name search (partial spelling)
- Genre filtering
- Year filtering
- Upload date filtering
- Popular this week (by download count)
- New releases (last 30 days)
- Top partnered DJs (by total revenue)
"""

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.tracks.models import Track
from apps.albums.models import AlbumPack
from apps.accounts.models import DJProfile
from apps.tracks.serializers import TrackSerializer
from apps.albums.serializers import AlbumPackSerializer


@api_view(['GET'])
def advanced_search(request):
    """
    Advanced search endpoint [Spec §8].
    Supports partial spelling, genre, year, date range.
    """
    query = request.query_params.get('q', '').strip()
    genre = request.query_params.get('genre', '').strip()
    year = request.query_params.get('year', '')
    date_from = request.query_params.get('date_from', '')
    content_type = request.query_params.get('type', 'all')  # 'all', 'tracks', 'albums', 'djs'

    results = {'tracks': [], 'albums': [], 'djs': []}

    # Base filters
    track_qs = Track.objects.filter(
        is_active=True, is_deleted=False, dj__profile__store_paused=False
    )
    album_qs = AlbumPack.objects.filter(
        is_active=True, is_deleted=False, dj__profile__store_paused=False
    )
    dj_qs = DJProfile.objects.filter(status='approved', profile__store_paused=False)

    # Text search (Fuzzy matching via TrigramSimilarity [Spec §8])
    from django.contrib.postgres.search import TrigramSimilarity

    if query:
        # Tracks
        track_qs = track_qs.annotate(
            similarity=TrigramSimilarity('title', query)
        ).filter(Q(similarity__gt=0.2) | Q(dj__dj_name__icontains=query)).order_by('-similarity')

        # Albums
        album_qs = album_qs.annotate(
            similarity=TrigramSimilarity('title', query)
        ).filter(Q(similarity__gt=0.2) | Q(dj__dj_name__icontains=query)).order_by('-similarity')

        # DJs
        dj_qs = dj_qs.annotate(
            similarity=TrigramSimilarity('dj_name', query)
        ).filter(similarity__gt=0.2).order_by('-similarity')

    # Genre filter
    if genre:
        track_qs = track_qs.filter(genre__icontains=genre)

    # Year filter
    if year:
        try:
            track_qs = track_qs.filter(year=int(year))
        except ValueError:
            pass

    # Date range filter
    if date_from:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(date_from)
            track_qs = track_qs.filter(created_at__gte=dt)
            album_qs = album_qs.filter(created_at__gte=dt)
        except (ValueError, TypeError):
            pass

    # Return results
    if content_type in ('all', 'tracks'):
        results['tracks'] = TrackSerializer(track_qs[:20], many=True).data
    if content_type in ('all', 'albums'):
        results['albums'] = AlbumPackSerializer(album_qs[:20], many=True).data
    if content_type in ('all', 'djs'):
        results['djs'] = [{
            'id': dj.id,
            'dj_name': dj.dj_name,
            'slug': dj.slug,
            'bio': dj.bio,
            'is_verified_dj': dj.profile.is_verified_dj,
            'is_pro_dj': dj.profile.is_pro_dj,
            'genres': dj.genres,
        } for dj in dj_qs[:20]]

    return Response(results)


@api_view(['GET'])
def popular_this_week(request):
    """Tracks popular this week by download count [Spec §8]."""
    tracks = Track.objects.filter(
        is_active=True, is_deleted=False, dj__profile__store_paused=False,
    ).order_by('-download_count')[:20]

    return Response({
        'tracks': TrackSerializer(tracks, many=True).data,
    })


@api_view(['GET'])
def new_releases(request):
    """New releases in the last 30 days [Spec §8]."""
    thirty_days_ago = timezone.now() - timedelta(days=30)

    tracks = Track.objects.filter(
        is_active=True, is_deleted=False, dj__profile__store_paused=False,
        created_at__gte=thirty_days_ago,
    ).order_by('-created_at')[:20]

    albums = AlbumPack.objects.filter(
        is_active=True, is_deleted=False, dj__profile__store_paused=False,
        created_at__gte=thirty_days_ago,
    ).order_by('-created_at')[:20]

    return Response({
        'tracks': TrackSerializer(tracks, many=True).data,
        'albums': AlbumPackSerializer(albums, many=True).data,
    })


@api_view(['GET'])
def top_partnered_djs(request):
    """Top partnered DJs by total revenue [Spec §8]."""
    djs = DJProfile.objects.filter(
        status='approved', profile__store_paused=False,
    ).order_by('-total_revenue')[:20]

    return Response({
        'djs': [{
            'id': dj.id,
            'dj_name': dj.dj_name,
            'slug': dj.slug,
            'is_verified_dj': dj.profile.is_verified_dj,
            'is_pro_dj': dj.profile.is_pro_dj,
            'genres': dj.genres,
            'total_revenue': str(dj.total_revenue),
        } for dj in djs],
    })
