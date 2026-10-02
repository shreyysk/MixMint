from django.shortcuts import render, get_object_or_404
from .models import DJProfile


def dj_storefront_view(request, slug):
    """DJ public storefront [Spec §3.2]."""
    dj = get_object_or_404(DJProfile, slug=slug, status="approved")

    # Don't show content if DJ store is paused [Spec §3.2]
    if dj.profile.store_paused:
        return render(request, "dj/store_paused.html", {"dj": dj})

    from apps.core.catalog import attach_stock

    tracks = list(dj.tracks.filter(is_active=True, is_deleted=False).select_related("dj", "dj__profile").order_by("-created_at"))
    albums = list(dj.albums.filter(is_active=True, is_deleted=False).select_related("dj", "dj__profile").order_by("-created_at"))
    attach_stock(tracks, "track")
    attach_stock(albums, "album")
    from apps.commerce.models import Bundle

    bundles = [b for b in Bundle.objects.filter(dj=dj, is_active=True, is_deleted=False).select_related("dj", "dj__profile")
               .prefetch_related("bundle_tracks__track").order_by("-created_at") if b.live_tracks()]
    popular = sorted(tracks, key=lambda t: (t.sales_last_7_days or 0, t.download_count or 0), reverse=True)
    drops = [t for t in tracks if t.copies_limit]
    genre_rows = []
    from collections import Counter

    for g, n in Counter((t.genre or "").strip() for t in tracks if t.genre).most_common(3):
        if n >= 3 and len(tracks) > 6:
            genre_rows.append({"id": "g-" + g.lower().replace(" ", "-"), "title": g, "items": [t for t in tracks if (t.genre or "").strip() == g]})

    # Fetch announcements [Imp 14]
    announcements = dj.announcements.filter(is_active=True).order_by("-created_at")[:5]

    # DJ-given offers surface on the storefront whenever one is live.
    from apps.admin_panel.models import PromotionalOffer

    dj_offers = PromotionalOffer.active_for_dj(dj)

    from apps.core.seo_utils import get_dj_storefront_og_tags

    # [Missing Item 02] Record storefront view
    try:
        from apps.accounts.utils import record_dj_page_view

        record_dj_page_view(dj.id, "storefront", request)
    except Exception:
        pass

    context = {
        "dj": dj,
        "tracks": tracks,
        "albums": albums,
        "bundles": bundles,
        "popular": popular[:12] if len(tracks) > 4 else [],
        "drops": drops,
        "genre_rows": genre_rows,
        "announcements": announcements,
        "dj_offers": dj_offers,
        "og_tags": get_dj_storefront_og_tags(dj),
    }
    return render(request, "dj/profile.html", context)
