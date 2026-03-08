def get_track_og_tags(track):
    """Generate OG tags for track detail page."""
    return {
        'og:title': f"{track.title} — {track.dj.dj_name} | MixMint",
        'og:description': (
            f"Buy and download '{track.title}' by {track.dj.dj_name}. "
            f"₹{track.price} · {track.genre} · mixmint.site"
        ),
        'og:image': track.artwork.url if track.artwork else 'https://mixmint.site/static/img/default-og.png',
        'og:url': f"https://mixmint.site/track/{track.id}",
        'og:type': 'music.song',
        'twitter:card': 'summary_large_image',
    }

def get_dj_storefront_og_tags(dj_profile):
    """Generate OG tags for DJ storefront."""
    bio = dj_profile.bio[:120] + "..." if len(dj_profile.bio) > 120 else dj_profile.bio
    return {
        'og:title': f"{dj_profile.dj_name} — DJ Storefront | MixMint",
        'og:description': (
            f"{bio} "
            f"Discover music from {dj_profile.dj_name} on MixMint."
        ),
        'og:image': dj_profile.profile.avatar_url if hasattr(dj_profile.profile, 'avatar_url') and dj_profile.profile.avatar_url else 'https://mixmint.site/static/img/default-dj-og.png',
        'og:url': f"https://mixmint.site/dj/{dj_profile.dj_name}",
        'og:type': 'profile',
    }

def get_default_og_tags():
    """Default tags for other pages."""
    return {
        'og:title': "MixMint — Home of DJ Releases",
        'og:description': "India's only DJ music marketplace where you truly own what you buy. Secure downloads, no streaming.",
        'og:image': 'https://mixmint.site/static/img/default-og.png',
        'og:url': 'https://mixmint.site',
        'og:type': 'website',
    }
