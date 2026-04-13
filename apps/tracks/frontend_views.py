from django.shortcuts import render, get_object_or_404
from django.utils.safestring import mark_safe
from .models import Track, TrackCollaborator
from apps.commerce.models import Purchase
from apps.downloads.utils import DownloadManager

def track_detail_view(request, pk):
    track = get_object_or_404(Track, pk=pk)

    def _build_preview_embed():
        if track.preview_type == 'youtube' and track.youtube_url:
            url = track.youtube_url.strip()
            if "watch?v=" in url:
                url = url.replace("watch?v=", "embed/")
            if "youtu.be/" in url:
                vid = url.split("youtu.be/", 1)[1].split("?", 1)[0]
                url = f"https://www.youtube.com/embed/{vid}"
            return mark_safe(
                f'<iframe class="w-full h-full" src="{url}" '
                f'title="YouTube preview" frameborder="0" allowfullscreen></iframe>'
            )

        if track.preview_type == 'instagram' and track.instagram_url:
            url = track.instagram_url.strip()
            embed_url = url
            if "/reel/" in url and not url.rstrip("/").endswith("/embed"):
                embed_url = url.rstrip("/") + "/embed"
            return mark_safe(
                f'<iframe class="w-full h-full" src="{embed_url}" '
                f'title="Instagram preview" frameborder="0"></iframe>'
            )

        return None

    preview_embed_html = _build_preview_embed()

    # Collaborators for display (if any)
    collaborators = TrackCollaborator.objects.filter(track=track).select_related('dj', 'dj__profile')

    purchase = None
    can_request_download = False
    needs_redownload_payment = False
    redownload_message = None

    if request.user.is_authenticated:
        profile = request.user.profile
        if getattr(track, 'is_external_link', False):
            # If external link, don't show normal download options or purchases
            pass
        elif track.price <= 0:
            can_request_download = True
        else:
            purchase = Purchase.objects.filter(
                user=profile,
                content_id=track.id,
                content_type='track',
                is_revoked=False,
                is_redownload=False,
            ).order_by('-created_at').first()

            if purchase and not purchase.download_completed:
                can_request_download = True
            elif purchase and purchase.download_completed:
                eligible, msg = DownloadManager.check_redownload_eligibility(profile, track.id, 'track')
                needs_redownload_payment = bool(eligible)
                redownload_message = msg
    
    from apps.core.seo_utils import get_track_og_tags

    # [Missing Item 02] Record track page view
    try:
        from apps.accounts.utils import record_dj_page_view
        record_dj_page_view(track.dj.id, 'track_page', request)
    except Exception:
        pass
    
    context = {
        'track': track,
        'preview_embed_html': preview_embed_html,
        'collaborators': collaborators,
        'purchase': purchase,
        'can_request_download': can_request_download,
        'needs_redownload_payment': needs_redownload_payment,
        'redownload_message': redownload_message,
        'og_tags': get_track_og_tags(track),
    }
    return render(request, 'tracks/detail.html', context)

def track_embed_view(request, pk):
    """Minimalist embeddable view for external sites [Imp 17]."""
    track = get_object_or_404(Track, pk=pk)
    
    def _build_preview_embed():
        if track.preview_type == 'youtube' and track.youtube_url:
            url = track.youtube_url.strip()
            if "watch?v=" in url:
                url = url.replace("watch?v=", "embed/")
            if "youtu.be/" in url:
                vid = url.split("youtu.be/", 1)[1].split("?", 1)[0]
                url = f"https://www.youtube.com/embed/{vid}"
            return mark_safe(
                f'<iframe class="w-full h-full" src="{url}" '
                f'title="YouTube preview" frameborder="0" allowfullscreen></iframe>'
            )

        if track.preview_type == 'instagram' and track.instagram_url:
            url = track.instagram_url.strip()
            embed_url = url
            if "/reel/" in url and not url.rstrip("/").endswith("/embed"):
                embed_url = url.rstrip("/") + "/embed"
            return mark_safe(
                f'<iframe class="w-full h-full" src="{embed_url}" '
                f'title="Instagram preview" frameborder="0"></iframe>'
            )
        return None

    context = {
        'track': track,
        'preview_embed_html': _build_preview_embed(),
    }
    return render(request, 'tracks/embed.html', context)


