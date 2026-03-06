from django.shortcuts import render, get_object_or_404
from django.utils.safestring import mark_safe
from .models import AlbumPack
from apps.commerce.models import Purchase
from apps.downloads.utils import DownloadManager

def album_detail_view(request, pk):
    album = get_object_or_404(AlbumPack, pk=pk)
    tracks = album.tracks.all().order_by('track_order')

    def _build_preview_embed():
        if album.preview_type == 'youtube' and album.youtube_url:
            url = album.youtube_url.strip()
            if "watch?v=" in url:
                url = url.replace("watch?v=", "embed/")
            if "youtu.be/" in url:
                vid = url.split("youtu.be/", 1)[1].split("?", 1)[0]
                url = f"https://www.youtube.com/embed/{vid}"
            return mark_safe(
                f'<iframe class="w-full h-full" src="{url}" '
                f'title="YouTube preview" frameborder="0" allowfullscreen></iframe>'
            )

        if album.preview_type == 'instagram' and album.instagram_url:
            url = album.instagram_url.strip()
            embed_url = url
            if "/reel/" in url and not url.rstrip("/").endswith("/embed"):
                embed_url = url.rstrip("/") + "/embed"
            return mark_safe(
                f'<iframe class="w-full h-full" src="{embed_url}" '
                f'title="Instagram preview" frameborder="0"></iframe>'
            )

        return None

    preview_embed_html = _build_preview_embed()

    purchase = None
    can_request_download = False
    needs_redownload_payment = False
    redownload_message = None

    if request.user.is_authenticated:
        profile = request.user.profile
        purchase = Purchase.objects.filter(
            user=profile,
            content_id=album.id,
            content_type='album',
            is_revoked=False,
            is_redownload=False,
        ).order_by('-created_at').first()

        if purchase and not purchase.download_completed:
            can_request_download = True
        elif purchase and purchase.download_completed:
            eligible, msg = DownloadManager.check_redownload_eligibility(profile, album.id, 'album')
            needs_redownload_payment = bool(eligible)
            redownload_message = msg
    
    context = {
        'album': album,
        'tracks': tracks,
        'preview_embed_html': preview_embed_html,
        'purchase': purchase,
        'can_request_download': can_request_download,
        'needs_redownload_payment': needs_redownload_payment,
        'redownload_message': redownload_message,
    }
    return render(request, 'albums/detail.html', context)
