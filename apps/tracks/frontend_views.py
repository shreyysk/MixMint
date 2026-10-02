from csp.decorators import csp_replace, csp_update  # noqa: F401
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.clickjacking import xframe_options_exempt

from apps.core.embeds import build_preview_embeds
from apps.downloads.utils import DownloadManager

from .models import Track, TrackCollaborator


def _safe_embed_src(url):
    """Kept for callers/tests: only http(s) URLs pass."""
    url = (url or "").strip()
    return url if url.lower().startswith(("http://", "https://")) else None


def _build_preview_embeds(track):
    """Both DJ embeds (YouTube and/or Instagram Reel), host-allowlisted. Never hosted audio."""
    return build_preview_embeds(track)


def _visible_track_or_404(request, pk):
    track = get_object_or_404(Track.objects.select_related("dj", "dj__profile"), pk=pk)
    if track.is_deleted or not track.is_active:
        is_owner = (
            request.user.is_authenticated
            and getattr(getattr(request.user.profile, "dj_profile", None), "id", None) == track.dj_id
        )
        if not (request.user.is_staff or is_owner):
            raise Http404("Track not found.")
    return track


def track_detail_view(request, pk):
    track = _visible_track_or_404(request, pk)
    preview_embeds = _build_preview_embeds(track)
    preview_embed_html = preview_embeds[0][2] if preview_embeds else None

    # Collaborators for display (if any)
    collaborators = TrackCollaborator.objects.filter(track=track).select_related("dj", "dj__profile")

    purchase = None
    can_request_download = False
    needs_redownload_payment = False
    redownload_message = None

    if request.user.is_authenticated:
        profile = request.user.profile
        if getattr(track, "is_external_link", False) or getattr(track, "source_url", None):
            # External tracks download ONLY via signed MixMint token (never the raw link).
            if track.price <= 0:
                can_request_download = True
            else:
                can_request_download = DownloadManager.owned_purchase(profile, track.id, "track") is not None
        elif track.price <= 0:
            can_request_download = True
        else:
            purchase = DownloadManager.owned_purchase(profile, track.id, "track")
            if purchase and not purchase.download_completed:
                can_request_download = True
            elif purchase and DownloadManager.has_active_insurance(purchase):
                can_request_download = True
            elif purchase:
                state, msg = DownloadManager.free_download_state(profile, track.id, "track")
                if state == "pay":
                    needs_redownload_payment = True
                else:  # still within the free downloads (device check happens when the link is made)
                    can_request_download = True
                redownload_message = msg

    from apps.core.seo_utils import get_track_og_tags

    # DJ-given offers surface on the track page whenever the DJ has a live one.
    from apps.admin_panel.models import PromotionalOffer

    dj_offers = PromotionalOffer.active_for_dj(track.dj)

    # [Missing Item 02] Record track page view
    try:
        from apps.accounts.utils import record_dj_page_view

        record_dj_page_view(track.dj.id, "track_page", request)
    except Exception:
        pass

    context = {
        "track": track,
        "preview_embed_html": preview_embed_html,
        "preview_embeds": preview_embeds,
        "collaborators": collaborators,
        "purchase": purchase,
        "can_request_download": can_request_download,
        "needs_redownload_payment": needs_redownload_payment,
        "redownload_message": redownload_message,
        "redownload_price": _redownload_price(track),
        "dj_offers": dj_offers,
        "og_tags": get_track_og_tags(track),
    }
    from apps.core.catalog import copies_left, savings_percent

    context["stock_left"] = copies_left(track, "track")
    context["savings"] = savings_percent(track.price, track.compare_at_price)
    context["more_from_dj"] = list(
        track.dj.tracks.filter(is_active=True, is_deleted=False).exclude(pk=track.pk).order_by("-created_at")[:4]
    )
    return render(request, "tracks/detail.html", context)


@xframe_options_exempt
@csp_replace(FRAME_ANCESTORS="*")  # replace 'none' (update would produce the invalid "'none' *")
def track_embed_view(request, pk):
    """Minimalist embeddable view for external sites [Imp 17]."""
    track = get_object_or_404(Track, pk=pk, is_active=True, is_deleted=False)
    embeds = _build_preview_embeds(track)

    context = {
        "track": track,
        "preview_embed_html": embeds[0][2] if embeds else None,
    }
    return render(request, "tracks/embed.html", context)


def _redownload_price(content):
    """What the buyer pays for a re-download (50% + buyer fee), in rupees."""
    from decimal import Decimal

    from apps.payments.views import calculate_total_price_paise

    try:
        return Decimal(calculate_total_price_paise(content, is_redownload=True)) / 100
    except Exception:
        return None
