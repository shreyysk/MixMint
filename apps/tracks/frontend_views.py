from django.shortcuts import render, get_object_or_404
from django.utils.safestring import mark_safe
from .models import Track, TrackCollaborator
from apps.commerce.models import Purchase
from apps.downloads.utils import DownloadManager


def _build_preview_embeds(track):
    """Build both DJ embeds (YouTube and/or Instagram Reel). Returns list of
    (key, label, html). Playback is from DJ embeds only — never hosted."""
    embeds = []
    if track.youtube_url:
        url = track.youtube_url.strip()
        if "watch?v=" in url:
            url = url.replace("watch?v=", "embed/")
        if "youtu.be/" in url:
            vid = url.split("youtu.be/", 1)[1].split("?", 1)[0]
            url = f"https://www.youtube.com/embed/{vid}"
        embeds.append(
            (
                "youtube",
                "Preview 1 · YouTube",
                mark_safe(
                    f'<iframe class="w-full h-full" src="{url}" '
                    f'title="YouTube preview" frameborder="0" allowfullscreen></iframe>'
                ),
            )
        )
    if track.instagram_url:
        url = track.instagram_url.strip()
        embed_url = url
        if "/reel/" in url and not url.rstrip("/").endswith("/embed"):
            embed_url = url.rstrip("/") + "/embed"
        embeds.append(
            (
                "instagram",
                "Preview 2 · Reel",
                mark_safe(
                    f'<iframe class="w-full h-full" src="{embed_url}" '
                    f'title="Instagram preview" frameborder="0"></iframe>'
                ),
            )
        )
    # Primary tab: preview_type if available, else first available.
    order = {"youtube": 0, "instagram": 1}
    primary = getattr(track, "preview_type", None)
    embeds.sort(key=lambda e: (0 if e[0] == primary else 1, order.get(e[0], 9)))
    return embeds


def track_detail_view(request, pk):
    track = get_object_or_404(Track, pk=pk)
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
                owned = Purchase.objects.filter(
                    user=profile,
                    content_id=track.id,
                    content_type="track",
                    status="paid",
                    is_revoked=False,
                ).exists()
                can_request_download = bool(owned)
        elif track.price <= 0:
            can_request_download = True
        else:
            purchase = (
                Purchase.objects.filter(
                    user=profile,
                    content_id=track.id,
                    content_type="track",
                    is_revoked=False,
                    is_redownload=False,
                )
                .order_by("-created_at")
                .first()
            )

            if purchase and not purchase.download_completed:
                can_request_download = True
            elif purchase and purchase.download_completed:
                eligible, msg = DownloadManager.check_redownload_eligibility(profile, track.id, "track")
                needs_redownload_payment = bool(eligible)
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
        "dj_offers": dj_offers,
        "og_tags": get_track_og_tags(track),
    }
    return render(request, "tracks/detail.html", context)


def track_embed_view(request, pk):
    """Minimalist embeddable view for external sites [Imp 17]."""
    track = get_object_or_404(Track, pk=pk)
    embeds = _build_preview_embeds(track)

    context = {
        "track": track,
        "preview_embed_html": embeds[0][2] if embeds else None,
    }
    return render(request, "tracks/embed.html", context)
