"""
DJ uploads: single tracks and album packs.

The page asks for a signed R2 URL per file (upload_url_view), the browser PUTs the file
straight to R2, then submits the form with the returned keys (upload_track_view POST).
"""

import json
import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.core import r2
from apps.core.embeds import instagram_code, youtube_id

logger = logging.getLogger("mixmint")

from apps.core.genres import GENRE_GROUPS, GENRES  # noqa: E402,F401


def _approved_dj(request):
    profile = request.user.profile
    dj = getattr(profile, "dj_profile", None) if hasattr(profile, "dj_profile") else None
    if profile.role != "dj" or dj is None or dj.status != "approved":
        return None
    if profile.is_banned or profile.is_frozen:
        return None
    return dj


@login_required
@require_POST
def upload_url_view(request):
    dj = _approved_dj(request)
    if dj is None:
        return JsonResponse({"error": "Only approved DJs can upload."}, status=403)
    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        return JsonResponse({"error": "Invalid request."}, status=400)
    try:
        return JsonResponse(r2.presign_upload(data.get("kind"), dj, data.get("filename", ""), data.get("size")))
    except r2.UploadError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except Exception:
        logger.exception("Could not create an upload URL for DJ %s", dj.id)
        return JsonResponse({"error": "Storage is unavailable right now. Please try again in a minute."}, status=502)


def _price(raw, kind):
    try:
        price = Decimal(str(raw).strip() or "x").quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        raise ValidationError("Enter a price in rupees, or 0 to give it away free.")
    minimum = Decimal(str(settings.MIN_ALBUM_PRICE if kind == "album" else settings.MIN_TRACK_PRICE))
    if kind == "album" and price < minimum:
        raise ValidationError(f"Album packs cost at least ₹{minimum:.0f}.")
    if kind == "track" and 0 < price < minimum:
        raise ValidationError(f"Paid tracks cost at least ₹{minimum:.0f} (or set 0 for free).")
    if price < 0 or price > 100000:
        raise ValidationError("That price doesn't look right.")
    return price


def _previews(post):
    yt = (post.get("youtube_url") or "").strip()
    ig = (post.get("instagram_url") or "").strip()
    if yt and not youtube_id(yt):
        raise ValidationError("That YouTube link doesn't look like a video link.")
    if ig and not instagram_code(ig):
        raise ValidationError("That Instagram link doesn't look like a Reel or post link.")
    if not (yt or ig):
        raise ValidationError("Add a YouTube or Instagram preview so buyers can hear it first.")
    return yt or None, ig or None, "youtube" if yt else "instagram"


def _offers(post, price):
    """(compare_at_price, copies_limit) from the optional 'Offers' fields."""
    was = None
    raw = (post.get("compare_at_price") or "").strip()
    if raw:
        try:
            was = Decimal(raw).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError):
            raise ValidationError("The 'was' price must be a number.")
        if was <= price:
            raise ValidationError("The 'was' price must be higher than the price (or leave it empty).")
    copies = _int_or_none(post.get("copies_limit"), 1, 100000) if (post.get("copies_limit") or "").strip() else None
    if (post.get("copies_limit") or "").strip() and copies is None:
        raise ValidationError("Limited copies must be a whole number from 1.")
    return was, copies


def _int_or_none(raw, lo, hi):
    try:
        v = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return v if lo <= v <= hi else None


def _first_error(exc):
    if hasattr(exc, "message_dict"):
        for errors in exc.message_dict.values():
            if errors:
                return errors[0]
    return exc.messages[0] if getattr(exc, "messages", None) else str(exc)


@login_required
def upload_track_view(request):
    """Upload page for tracks and album packs [Spec P3 §4]."""
    profile = request.user.profile
    if profile.role != "dj" or not hasattr(profile, "dj_profile"):
        return redirect("dashboard")
    dj = _approved_dj(request)
    ctx = {
        "storage_ready": r2.configured(),
        "covers_ready": bool(r2.public_url("x")),
        "approved": dj is not None,
        "genre_choices": GENRES, "genre_groups": GENRE_GROUPS,
        "min_track_price": int(settings.MIN_TRACK_PRICE),
        "min_album_price": int(settings.MIN_ALBUM_PRICE),
        "kind": "album" if request.GET.get("kind") == "album" else "track",
    }
    if request.method != "POST":
        return render(request, "dashboard/upload.html", ctx)
    if dj is None:
        messages.error(request, "Your DJ account isn't approved yet, so you can't upload.")
        return redirect("dj_dashboard")

    post = request.POST
    kind = "album" if post.get("kind") == "album" else "track"
    try:
        if post.get("content_responsibility_accepted") not in ("on", "true", "1"):
            raise ValidationError("Please confirm you have the rights to sell this.")
        title = (post.get("title") or "").strip()[:255]
        if not title:
            raise ValidationError("Give it a title.")
        price = _price(post.get("price"), kind)
        yt, ig, preview_type = _previews(post)
        file_key = post.get("file_key", "")
        size = r2.uploaded_size("album" if kind == "album" else "audio", dj, file_key)
        cover_url = (post.get("cover_url") or "").strip()
        if cover_url:
            r2.cover_key_from_url(cover_url, dj)
        was, copies = _offers(post, price)
        common = dict(
            compare_at_price=was,
            copies_limit=copies,
            dj=dj,
            title=title,
            description=(post.get("description") or "").strip()[:5000] or None,
            price=price,
            file_key=file_key,
            file_size=size,
            preview_type=preview_type,
            youtube_url=yt,
            instagram_url=ig,
        )
        if kind == "album":
            from apps.albums.models import AlbumPack

            item = AlbumPack(
                **common,
                cover_image=cover_url or None,
                track_count=_int_or_none(post.get("track_count"), 1, 500) or 0,
                upload_method="direct_zip",
                processing_status="completed",
            )
            item.full_clean()
            item.save()
        else:
            from apps.tracks.models import Track

            ext = file_key.rsplit(".", 1)[-1].lower()
            item = Track(
                **common,
                cover_url=cover_url or None,
                genre=(post.get("genre") or "").strip()[:100] or None,
                bpm=_int_or_none(post.get("bpm"), 40, 250),
                year=_int_or_none(post.get("year"), 1950, 2100),
                file_format={"aif": "aiff"}.get(ext, ext) if ext in ("mp3", "wav", "flac", "aiff", "aif") else "wav",
            )
            item.save()  # Track.save() runs full_clean()
            _tag_track(item)
    except r2.UploadError as exc:
        messages.error(request, str(exc))
        return render(request, "dashboard/upload.html", {**ctx, "form": post, "kind": kind}, status=400)
    except ValidationError as exc:
        messages.error(request, _first_error(exc))
        return render(request, "dashboard/upload.html", {**ctx, "form": post, "kind": kind}, status=400)

    from apps.admin_panel.vault import archive_after_upload

    archive_after_upload(kind, item)
    messages.success(request, f"“{item.title}” is live in your store. Promote it with free covers from the DJ Asset Pack (DJ dashboard → Asset pack).")
    return redirect("album_detail" if kind == "album" else "track_detail", pk=item.pk)


def _tag_track(track):
    """Write MixMint ID3 tags + checksum now for small files; large ones are left as uploaded
    (a serverless request can't download and re-upload hundreds of MB in time)."""
    if (track.file_size or 0) > getattr(settings, "DOWNLOAD_PROXY_MAX_MB", 40) * 1024 * 1024:
        return
    try:
        from apps.tracks.tasks import process_track_metadata_task

        process_track_metadata_task.delay(track.id)
    except Exception:
        logger.exception("Metadata task could not start for track %s", track.id)
