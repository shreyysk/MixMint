from django.http import Http404
from django.shortcuts import get_object_or_404, render

from apps.core.embeds import build_preview_embeds
from apps.downloads.utils import DownloadManager

from .models import AlbumPack


def album_detail_view(request, pk):
    album = get_object_or_404(AlbumPack.objects.select_related("dj", "dj__profile"), pk=pk)
    if album.is_deleted or not album.is_active:
        is_owner = (
            request.user.is_authenticated
            and getattr(getattr(request.user.profile, "dj_profile", None), "id", None) == album.dj_id
        )
        if not (request.user.is_staff or is_owner):
            raise Http404("Album not found.")
    tracks = album.tracks.all().order_by("track_order")
    embeds = build_preview_embeds(album)
    preview_embed_html = embeds[0][2] if embeds else None

    purchase = None
    can_request_download = False
    needs_redownload_payment = False
    redownload_message = None

    if request.user.is_authenticated:
        profile = request.user.profile
        purchase = DownloadManager.owned_purchase(profile, album.id, "album")
        if purchase and (not purchase.download_completed or DownloadManager.has_active_insurance(purchase)):
            can_request_download = True
        elif purchase:
            eligible, msg = DownloadManager.check_redownload_eligibility(profile, album.id, "album")
            needs_redownload_payment = bool(eligible)
            redownload_message = msg

    context = {
        "album": album,
        "tracks": tracks,
        "preview_embed_html": preview_embed_html,
        "preview_embeds": embeds,
        "purchase": purchase,
        "can_request_download": can_request_download,
        "needs_redownload_payment": needs_redownload_payment,
        "redownload_message": redownload_message,
        "redownload_price": _redownload_price(album),
    }
    try:
        from apps.admin_panel.models import PromotionalOffer

        context["dj_offers"] = PromotionalOffer.active_for_dj(album.dj)
    except Exception:
        context["dj_offers"] = []
    return render(request, "albums/detail.html", context)


def _redownload_price(content):
    """What the buyer pays for a re-download (50% + buyer fee), in rupees."""
    from decimal import Decimal

    from apps.payments.views import calculate_total_price_paise

    try:
        return Decimal(calculate_total_price_paise(content, is_redownload=True)) / 100
    except Exception:
        return None
