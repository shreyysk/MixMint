"""
MixMint Listener Views [Spec §3.1].

Listener-specific endpoints:
- Download history (only successful completions)
- Purchase history
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.downloads.models import DownloadLog
from apps.commerce.models import Purchase


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_history(request):
    """
    View download history — only after successful completion [Spec §3.1].
    Shows only completed downloads with checksum verification.
    """
    profile = request.user.profile

    logs = DownloadLog.objects.filter(
        user=profile,
        completed=True,
        checksum_verified=True,
    ).order_by('-created_at')[:50]

    data = [{
        'content_id': log.content_id,
        'content_type': log.content_type,
        'ip_address': log.ip_address,
        'attempt_number': log.attempt_number,
        'downloaded_at': log.created_at.isoformat(),
    } for log in logs]

    return Response({'downloads': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def purchase_history(request):
    """
    View purchase history — only completed purchases with download [Spec §3.1].
    Purchase becomes visible only after download is complete.
    """
    profile = request.user.profile

    purchases = Purchase.objects.filter(
        user=profile,
        status='paid',
        download_completed=True,
    ).order_by('-created_at')[:50]

    # Enrich with content titles
    from apps.tracks.models import Track
    from apps.albums.models import AlbumPack

    data = []
    for p in purchases:
        entry = {
            'id': p.id,
            'content_type': p.content_type,
            'content_id': p.content_id,
            'price_paid': str(p.price_paid),
            'is_redownload': p.is_redownload,
            'purchased_at': p.created_at.isoformat(),
        }
        try:
            if p.content_type == 'track':
                track = Track.objects.get(id=p.content_id)
                entry['title'] = track.title
                entry['dj_name'] = track.dj.dj_name
            elif p.content_type == 'album':
                album = AlbumPack.objects.get(id=p.content_id)
                entry['title'] = album.title
                entry['dj_name'] = album.dj.dj_name
        except (Track.DoesNotExist, AlbumPack.DoesNotExist):
            entry['title'] = 'Content removed'
            entry['dj_name'] = 'N/A'
        data.append(entry)

    return Response({'purchases': data})
