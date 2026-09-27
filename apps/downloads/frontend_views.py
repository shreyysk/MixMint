"""
Frontend view for the buyer-facing download page [Spec §8].
Shows token countdown, progress bar, and attempt tracking.
"""

from apps.core.net import get_client_ip
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
    if token.content_type == "track":
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

    # Attempts used on this network for this item (same counter the token endpoint enforces).
    from .models import DownloadAttempt

    attempt = DownloadAttempt.objects.filter(
        user=request.user.profile,
        ip_address=get_client_ip(request),
        content_id=token.content_id,
        content_type=token.content_type,
    ).first()
    attempt_count = attempt.attempt_count if attempt else 0

    # Build the actual download URL (secure streaming proxy).
    # Must match config/urls.py mount: api/v1/downloads/ + downloads/urls.py.
    download_url = f"/api/v1/downloads/{token_str}/"

    # Expiry warning: flag when <10h remain so buyers hurry (short tokens warn immediately).
    from django.conf import settings

    warn_hours = getattr(settings, "DOWNLOAD_EXPIRY_WARNING_HOURS", 10)

    context = {
        "token": token,
        "content_title": content_title,
        "content_type": token.content_type,
        "download_url": download_url,
        "token_seconds_remaining": max(0, seconds_remaining),
        "expiry_warning": bool(token.expires_at and token.expires_at > now) and seconds_remaining < warn_hours * 3600,
        "attempt_count": attempt_count,
        "max_attempts": getattr(settings, "MAX_DOWNLOAD_ATTEMPTS", 3),
        "status_url": f"/api/v1/downloads/status/{token_str}/",
        "content_url": f"/{'tracks' if token.content_type == 'track' else 'albums'}/{token.content_id}/",
    }
    return render(request, "downloads/download_page.html", context)


@login_required
def download_status_view(request, token_str):
    """Real completion status for the download page (server-side byte + checksum verification)."""
    from django.http import JsonResponse

    token = DownloadToken.objects.filter(token=token_str, user=request.user.profile).first()
    if token is None:
        return JsonResponse({"error": "Not found."}, status=404)
    return JsonResponse(
        {
            "is_used": token.is_used,
            "bytes_expected": token.bytes_expected,
            "bytes_delivered": token.bytes_delivered,
            "download_completed": token.download_completed,
            "checksum_failed": bool(token.bytes_delivered and not token.checksum_verified and token.checksum_hex),
        }
    )
