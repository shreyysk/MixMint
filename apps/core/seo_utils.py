from django.conf import settings


def _site():
    return (getattr(settings, "BASE_URL", "") or "https://mixmint.site").rstrip("/")


def get_track_og_tags(track):
    """Generate OG tags for track detail page."""
    from apps.tracks.templatetags.tracks_filters import price_label

    genre = f" · {track.genre}" if track.genre else ""
    return {
        "og:title": f"{track.title} — {track.dj.dj_name} | MixMint",
        "og:description": (
            f"Support and download '{track.title}' by {track.dj.dj_name}. "
            f"{price_label(track.price)}{genre} · MixMint"
        ),
        "og:image": track.cover_url or f"{_site()}/static/brand/og-default.png",
        "og:url": f"{_site()}/tracks/{track.id}/",
        "og:type": "music.song",
        "twitter:card": "summary_large_image",
    }


def get_dj_storefront_og_tags(dj_profile):
    """Generate OG tags for DJ storefront."""
    bio = dj_profile.bio or ""
    bio_trimmed = bio[:120] + "..." if len(bio) > 120 else bio
    return {
        "og:title": f"{dj_profile.dj_name} — DJ Storefront | MixMint",
        "og:description": (f"{bio_trimmed} " f"Discover music from {dj_profile.dj_name} on MixMint."),
        "og:image": (
            getattr(dj_profile, "banner_url", None)
            or getattr(dj_profile.profile, "avatar_url", None)
            or f"{_site()}/static/brand/og-default.png"
        ),
        "og:url": f"{_site()}/dj/{dj_profile.slug}/",
        "og:type": "profile",
    }


def get_default_og_tags():
    """Default tags for other pages."""
    return {
        "og:title": "MixMint — Home of DJ Releases",
        "og:description": (
            "Buy DJ edits, remixes, album packs and sample packs straight from India's DJs: "
            "Tulu, Kannada, Bollywood, house and more. Preview, pay with UPI, download instantly."
        ),
        "og:image": f"{_site()}/static/brand/og-default.png",
        "og:url": "https://mixmint.site",
        "og:type": "website",
    }


# ─────────────────────────────── structured data (JSON-LD) ───────────────────────────────
# Google reads these to show price, availability and the artist right in search results.
import json as _json

DEFAULT_IMAGE = "/static/brand/og-default.png"


def ld_json(*objs):
    """Serialize schema.org objects for a <script type="application/ld+json"> (safe inside HTML)."""
    data = objs[0] if len(objs) == 1 else list(objs)
    return _json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _offer(price, url):
    return {"@type": "Offer", "price": f"{price or 0:.2f}", "priceCurrency": "INR", "availability": "https://schema.org/InStock",
            "url": url, "seller": {"@type": "Organization", "name": "MixMint"}}


def _crumbs(*pairs):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": name, "item": f"{_site()}{path}"} for i, (name, path) in enumerate(pairs)]}


def site_ld():
    s = _site()
    return ld_json({"@context": "https://schema.org", "@graph": [
        {"@type": "Organization", "@id": f"{s}/#org", "name": "MixMint", "url": s, "logo": f"{s}/static/brand/profile-mint.png",
         "slogan": "Home of DJ Releases", "areaServed": "IN"},
        {"@type": "WebSite", "@id": f"{s}/#site", "url": s, "name": "MixMint", "publisher": {"@id": f"{s}/#org"},
         "potentialAction": {"@type": "SearchAction", "target": f"{s}/releases/?q={{search_term_string}}",
                             "query-input": "required name=search_term_string"}},
    ]})


def track_ld(track):
    s, url = _site(), f"{_site()}/tracks/{track.id}/"
    rec = {"@type": ["Product", "MusicRecording"], "name": track.title, "url": url,
           "image": track.cover_url or s + DEFAULT_IMAGE, "byArtist": {"@type": "Person", "name": track.dj.dj_name, "url": f"{s}/dj/{track.dj.slug}/"},
           "brand": {"@type": "Brand", "name": track.dj.dj_name},
           "description": (track.description or f"{track.title} by {track.dj.dj_name}. Instant download on MixMint.")[:300],
           "offers": _offer(track.price, url)}
    if track.genre:
        rec["genre"] = track.genre
    return ld_json({"@context": "https://schema.org", "@graph": [rec, _crumbs(("Releases", "/releases/"), (track.title, f"/tracks/{track.id}/"))]})


def album_ld(album):
    s, url = _site(), f"{_site()}/albums/{album.id}/"
    rec = {"@type": ["Product", "MusicAlbum"] if album.pack_type == "album" else "Product", "name": album.title, "url": url,
           "image": album.cover_image or s + DEFAULT_IMAGE, "brand": {"@type": "Brand", "name": album.dj.dj_name},
           "category": album.get_pack_type_display(),
           "description": (album.description or f"{album.get_pack_type_display()} by {album.dj.dj_name} on MixMint.")[:300],
           "offers": _offer(album.price, url)}
    if album.pack_type == "album":
        rec["byArtist"] = {"@type": "Person", "name": album.dj.dj_name, "url": f"{s}/dj/{album.dj.slug}/"}
        if album.track_count:
            rec["numTracks"] = album.track_count
    return ld_json({"@context": "https://schema.org", "@graph": [rec, _crumbs(("Releases", "/releases/"), (album.title, f"/albums/{album.id}/"))]})


def dj_ld(dj):
    s = _site()
    same = [v for v in (dj.social_links or {}).values() if isinstance(v, str) and v.startswith("http")] if isinstance(dj.social_links, dict) else []
    p = {"@type": "Person", "name": dj.dj_name, "url": f"{s}/dj/{dj.slug}/", "jobTitle": "DJ", "description": (dj.bio or "")[:300] or None,
         "image": getattr(dj, "banner_url", None) or None, "homeLocation": dj.location or None, "sameAs": same or None}
    return ld_json({"@context": "https://schema.org", **{k: v for k, v in p.items() if v}})


def get_album_og_tags(album):
    from apps.tracks.templatetags.tracks_filters import price_label

    kind = album.get_pack_type_display()
    return {
        "og:title": f"{album.title} — {album.dj.dj_name} | MixMint",
        "og:description": f"{kind} by {album.dj.dj_name}. {price_label(album.price)} · instant download on MixMint.",
        "og:image": album.cover_image or f"{_site()}{DEFAULT_IMAGE}",
        "og:url": f"{_site()}/albums/{album.id}/",
        "og:type": "music.album" if album.pack_type == "album" else "product",
        "twitter:card": "summary_large_image",
    }
