"""
Safe preview embeds. DJ-supplied URLs are untrusted: we only ever emit
iframes pointing at YouTube / Instagram embed endpoints built from a parsed ID,
so no arbitrary page can be framed and no attribute can be injected.
"""

import re
from urllib.parse import parse_qs, urlparse

from django.utils.html import format_html

_YT_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtube-nocookie.com",
    "youtube-nocookie.com",
}
_IG_HOSTS = {"instagram.com", "www.instagram.com"}
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,20}$")


def youtube_id(url):
    try:
        parsed = urlparse((url or "").strip())
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https") or (parsed.hostname or "").lower() not in _YT_HOSTS:
        return None
    host = parsed.hostname.lower()
    parts = [p for p in parsed.path.split("/") if p]
    vid = None
    if host == "youtu.be" and parts:
        vid = parts[0]
    elif parsed.path == "/watch":
        vid = (parse_qs(parsed.query).get("v") or [None])[0]
    elif len(parts) >= 2 and parts[0] in ("embed", "shorts", "live", "v"):
        vid = parts[1]
    return vid if vid and _ID_RE.match(vid) else None


def instagram_code(url):
    try:
        parsed = urlparse((url or "").strip())
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https") or (parsed.hostname or "").lower() not in _IG_HOSTS:
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2 and parts[0] in ("reel", "reels", "p", "tv"):
        code = parts[1]
        return code if re.match(r"^[A-Za-z0-9_-]{5,40}$", code) else None
    return None


def youtube_embed(url):
    vid = youtube_id(url)
    if not vid:
        return None
    return format_html(
        '<iframe class="w-full h-full" src="https://www.youtube-nocookie.com/embed/{}?rel=0" title="YouTube preview" '
        'loading="lazy" allow="encrypted-media; picture-in-picture" referrerpolicy="strict-origin-when-cross-origin" '
        "allowfullscreen></iframe>",
        vid,
    )


def instagram_embed(url):
    code = instagram_code(url)
    if not code:
        return None
    return format_html(
        '<iframe class="w-full h-full" src="https://www.instagram.com/reel/{}/embed" title="Instagram preview" '
        'loading="lazy" scrolling="no"></iframe>',
        code,
    )


def build_preview_embeds(obj):
    """[(key, label, html)] for an object with youtube_url / instagram_url / preview_type."""
    embeds = []
    yt = youtube_embed(getattr(obj, "youtube_url", None))
    if yt:
        embeds.append(("youtube", "Preview 1 · YouTube", yt))
    ig = instagram_embed(getattr(obj, "instagram_url", None))
    if ig:
        embeds.append(("instagram", "Preview 2 · Reel", ig))
    primary = getattr(obj, "preview_type", None)
    embeds.sort(key=lambda e: 0 if e[0] == primary else 1)
    return embeds
