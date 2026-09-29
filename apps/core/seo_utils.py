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
        "og:image": track.cover_url or f"{_site()}/static/logo/MIXMINT_WHITE.png",
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
            dj_profile.profile.avatar_url
            if hasattr(dj_profile.profile, "avatar_url") and dj_profile.profile.avatar_url
            else f"{_site()}/static/logo/MIXMINT_WHITE.png"
        ),
        "og:url": f"{_site()}/dj/{dj_profile.slug}/",
        "og:type": "profile",
    }


def get_default_og_tags():
    """Default tags for other pages."""
    return {
        "og:title": "MixMint — Home of DJ Releases",
        "og:description": (
            "India's only DJ music marketplace where you truly support your favorite artists. "
            "Secure downloads, no streaming."
        ),
        "og:image": "https://mixmint.site/static/img/default-og.png",
        "og:url": "https://mixmint.site",
        "og:type": "website",
    }
