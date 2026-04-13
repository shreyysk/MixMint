"""
Frontend view for the buyer-facing download page [Spec §8].
Shows token countdown, progress bar, and attempt tracking.
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.utils import timezone
from .models import DownloadToken
from apps.tracks.models import Track
from apps.albums.models import AlbumPack


@login_required
def download_page_view(request, token_str):
    """
    Renders the download page UI for a given token.
    The actual file streaming is handled by download_content view.
    """
    try:
        token = DownloadToken.objects.get(
            token=token_str,
            user=request.user.profile,
        )
    except DownloadToken.DoesNotExist:
        raise Http404("Invalid or expired download token.")

    # Resolve content details for display
    if token.content_type == 'track':
        content = get_object_or_404(Track, id=token.content_id)
        content_title = content.title
    else:
        content = get_object_or_404(AlbumPack, id=token.content_id)
        content_title = content.title

    # Calculate time remaining
    now = timezone.now()
    if token.expires_at and token.expires_at > now:
        seconds_remaining = int((token.expires_at - now).total_seconds())
    else:
        seconds_remaining = 0

    # Get attempt count for this content
    from django.core.cache import cache
    attempt_key = f"dl_attempts_{request.META.get('REMOTE_ADDR')}_{token.content_id}_{token.content_type}"
    attempt_count = cache.get(attempt_key, 0)

    # Build the actual download URL (streaming proxy)
    download_url = f"/downloads/{token_str}/"

    context = {
        'token': token,
        'content_title': content_title,
        'content_type': token.content_type,
        'download_url': download_url,
        'token_seconds_remaining': max(0, seconds_remaining),
        'attempt_count': attempt_count,
        'max_attempts': 3,
    }
    return render(request, 'downloads/download_page.html', context)
