"""DJ tools after upload: edit or remove a track / album, and edit the public store profile."""

from urllib.parse import urlsplit

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core import r2

from .upload_views import GENRES, _first_error, _int_or_none, _offers, _previews, _price

SOCIAL = [
    ("instagram", "Instagram", "instagram.com"),
    ("youtube", "YouTube", "youtube.com"),
    ("soundcloud", "SoundCloud", "soundcloud.com"),
    ("spotify", "Spotify", "spotify.com"),
    ("mixcloud", "Mixcloud", "mixcloud.com"),
    ("website", "Website", ""),
]


def _dj(request):
    profile = request.user.profile
    dj = getattr(profile, "dj_profile", None) if hasattr(profile, "dj_profile") else None
    if profile.role != "dj" or dj is None:
        return None
    return dj


def _model(kind):
    if kind == "track":
        from apps.tracks.models import Track

        return Track
    if kind == "album":
        from apps.albums.models import AlbumPack

        return AlbumPack
    raise Http404


def _own_image(url, dj):
    """Accept an image URL only if it's one this DJ uploaded to our public bucket (or unchanged)."""
    url = (url or "").strip()
    if not url:
        return None
    r2.cover_key_from_url(url, dj)
    return url


@login_required
def edit_music_view(request, kind, pk):
    dj = _dj(request)
    if dj is None:
        return redirect("dashboard")
    item = get_object_or_404(_model(kind), pk=pk, dj=dj, is_deleted=False)
    cover_field = "cover_image" if kind == "album" else "cover_url"
    ctx = {"item": item, "kind": kind, "genre_choices": GENRES, "cover": getattr(item, cover_field) or ""}

    if request.method == "POST":
        post = request.POST
        try:
            title = (post.get("title") or "").strip()[:255]
            if not title:
                raise ValidationError("Give it a title.")
            item.title = title
            item.description = (post.get("description") or "").strip()[:5000] or None
            item.price = _price(post.get("price"), kind)
            item.compare_at_price, item.copies_limit = _offers(post, item.price)
            item.youtube_url, item.instagram_url, item.preview_type = _previews(post)
            new_cover = (post.get("cover_url") or "").strip()
            if new_cover != (getattr(item, cover_field) or ""):
                setattr(item, cover_field, _own_image(new_cover, dj))
            item.is_active = post.get("is_active") == "on"
            if kind == "track":
                item.genre = (post.get("genre") or "").strip()[:100] or None
                item.bpm = _int_or_none(post.get("bpm"), 40, 250)
                item.year = _int_or_none(post.get("year"), 1950, 2100)
            else:
                item.track_count = _int_or_none(post.get("track_count"), 1, 500) or item.track_count
            item.full_clean()
            item.save()
        except r2.UploadError as exc:
            messages.error(request, str(exc))
            return render(request, "dashboard/edit_music.html", ctx, status=400)
        except ValidationError as exc:
            messages.error(request, _first_error(exc))
            return render(request, "dashboard/edit_music.html", ctx, status=400)
        messages.success(request, "Saved." if item.is_active else "Saved. It's hidden from your store for now.")
        return redirect("dj_dashboard")
    return render(request, "dashboard/edit_music.html", ctx)


@login_required
@require_POST
def delete_music_view(request, kind, pk):
    """Soft delete: gone from the store, but people who bought it keep it in their library."""
    dj = _dj(request)
    if dj is None:
        return redirect("dashboard")
    item = get_object_or_404(_model(kind), pk=pk, dj=dj, is_deleted=False)
    item.is_deleted, item.is_active = True, False
    item.save(update_fields=["is_deleted", "is_active"])
    messages.success(request, f"“{item.title}” was removed from your store. Past buyers keep their copy.")
    return redirect("dj_dashboard")


def _clean_link(value, domain):
    value = (value or "").strip()
    if not value:
        return ""
    if not value.startswith(("http://", "https://")):
        value = "https://" + value
    parts = urlsplit(value)
    host = (parts.hostname or "").lower()
    if not host or "." not in host:
        raise ValidationError(f"“{value}” doesn't look like a web address.")
    if domain and not (host == domain or host.endswith("." + domain)):
        raise ValidationError(f"That doesn't look like a {domain} link.")
    return value[:300]


@login_required
def store_profile_view(request):
    dj = _dj(request)
    if dj is None:
        return redirect("dashboard")
    profile = dj.profile
    links = dict(dj.social_links or {})
    ctx = {"dj": dj, "links": links, "social": SOCIAL}

    if request.method == "POST":
        post = request.POST
        try:
            name = (post.get("dj_name") or "").strip()[:100]
            if not name:
                raise ValidationError("Your DJ name can't be empty.")
            new_links = {}
            for key, _label, domain in SOCIAL:
                v = _clean_link(post.get(key), domain)
                if v:
                    new_links[key] = v
            avatar = (post.get("avatar_url") or "").strip()
            banner = (post.get("banner_url") or "").strip()
            if avatar != (profile.avatar_url or ""):
                profile.avatar_url = _own_image(avatar, dj)
            if banner != (dj.banner_url or ""):
                dj.banner_url = _own_image(banner, dj)
        except r2.UploadError as exc:
            messages.error(request, str(exc))
            return render(request, "dashboard/store_profile.html", ctx, status=400)
        except ValidationError as exc:
            messages.error(request, _first_error(exc))
            return render(request, "dashboard/store_profile.html", ctx, status=400)

        import re

        dj.dj_name = name
        dj.bio = (post.get("bio") or "").strip()[:2000] or None
        dj.location = (post.get("location") or "").strip()[:255] or None
        dj.genres = [g.strip()[:40] for g in re.split(r"[,/|]+", post.get("genres") or "") if g.strip()][:10]
        dj.social_links = new_links
        dj.save(update_fields=["dj_name", "bio", "location", "genres", "social_links", "banner_url"])
        profile.save(update_fields=["avatar_url"])
        paused = post.get("store_paused") == "on"
        if paused != profile.store_paused:
            profile.store_paused = paused
            profile.save(update_fields=["store_paused"])
        messages.success(request, "Store profile saved.")
        return redirect("dj_store_profile")
    return render(request, "dashboard/store_profile.html", ctx)
