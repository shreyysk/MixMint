"""
External-source downloads: DJ Drive/MediaFire link -> MixMint signed endpoint.

Flow: buyer purchases -> backend issues token (no fetch yet) -> first hit to
the download endpoint lazy-fetches server-side -> temp cache -> streams cached
file -> cleanup job deletes cache after expiry/use limit.

The buyer only ever sees mixmint.app/.../<token>/ — source URL never exposed.
"""

import logging
import os

from django.conf import settings
from django.core.cache import cache
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.tracks.models import Track

from .models import DownloadToken
from .source_fetch import fetch_from_source
from .utils import DownloadManager

logger = logging.getLogger("mixmint")

RATE_LIMIT = 30  # hits per hour per user/IP
RATE_WINDOW = 3600


def _rate_limited(scope):
    key = f"ext_dl_rate_{scope}"
    try:
        hits = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=RATE_WINDOW)
        hits = 1
    return hits > RATE_LIMIT


def _request_profile(request):
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return None
    return getattr(user, "profile", None)


def _owns_content(profile, content_type, content_id):
    from apps.commerce.models import Purchase

    return Purchase.objects.filter(
        user=profile,
        content_type=content_type,
        content_id=content_id,
        status="paid",
        is_revoked=False,
    ).exists()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def issue_external_token(request):
    """Issue a signed, expiring, limited-use token for an external-source track.

    Body: {"content_type": "track", "content_id": 123}
    Only the purchasing owner may mint a token. No source URL in response.
    """
    profile = _request_profile(request)
    if profile is None:
        return Response({"error": "Authentication required."}, status=401)

    content_type = request.data.get("content_type", "track")
    content_id = request.data.get("content_id")
    if content_type not in ("track", "album") or not content_id:
        return Response({"error": "Only track/album external downloads are supported."}, status=400)

    if content_type == "track":
        from apps.tracks.models import Track as ContentModel
    else:
        from apps.albums.models import AlbumPack as ContentModel
    content = get_object_or_404(ContentModel, id=content_id, is_active=True, is_deleted=False)
    is_external = bool(getattr(content, "is_external_link", False) or getattr(content, "source_url", None))
    if not is_external:
        return Response({"error": "Content is not an external-source item."}, status=400)
    is_free = (content.price or 0) <= 0
    if not is_free and not _owns_content(profile, content_type, content.id):
        return Response({"error": "Purchase required before download."}, status=403)

    if _rate_limited(f"issue_{profile.pk}"):
        return Response({"error": "Too many download requests. Try again later."}, status=429)

    token = DownloadToken.create_external_token(
        user=profile,
        content_type=content_type,
        content_id=content.id,
        expiry_minutes=getattr(settings, "EXTERNAL_DOWNLOAD_TOKEN_MINUTES", 15),
        max_downloads=getattr(settings, "EXTERNAL_DOWNLOAD_MAX_USES", 1),
        access_source="free" if is_free else "purchase",
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        device_hash=request.META.get("HTTP_X_DEVICE_HASH"),
    )
    DownloadManager.create_download_log(
        user=profile,
        content_id=content.id,
        content_type=content_type,
        ip_address=request.META.get("REMOTE_ADDR"),
        device_hash=request.META.get("HTTP_X_DEVICE_HASH"),
    )
    return Response(
        {
            "token": token.token,
            "download_url": f"/api/v1/downloads/external/{token.token}/",
            "expires_at": token.expires_at.isoformat(),
            "max_downloads": token.max_downloads,
        },
        status=201,
    )


def download_external(request, token_str):
    """Stream cached file for a valid external token (session or JWT auth).

    URL seen by buyer reveals nothing about Drive/MediaFire.
    """
    try:
        dl = DownloadToken.objects.select_related("user", "user__user").get(token=token_str)
    except DownloadToken.DoesNotExist:
        return JsonResponse({"error": "Invalid download link."}, status=403)

    # Owner check: token bound to purchasing user.
    req_user = getattr(request, "user", None)
    if not req_user or not getattr(req_user, "is_authenticated", False):
        return JsonResponse({"error": "Authentication required."}, status=401)
    if dl.user.user_id != req_user.id:
        return JsonResponse({"error": "This download link belongs to another account."}, status=403)

    if dl.is_expired or not dl.is_active:
        return JsonResponse({"error": "Link expired."}, status=403)

    client_ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR")
    if _rate_limited(f"hit_{dl.user_id}") or _rate_limited(f"ip_{client_ip}"):
        return JsonResponse({"error": "Too many download attempts. Try again later."}, status=429)

    if dl.content_type == "track":
        content = get_object_or_404(Track, id=dl.content_id, is_active=True, is_deleted=False)
    elif dl.content_type == "album":
        from apps.albums.models import AlbumPack

        content = get_object_or_404(AlbumPack, id=dl.content_id, is_active=True, is_deleted=False)
    else:
        return JsonResponse({"error": "Unsupported content type."}, status=400)
    source_url = getattr(content, "source_url", None) or content.external_link_url
    source_type = getattr(content, "source_type", None) or (content.external_link_provider or "other")
    if not source_url:
        return JsonResponse({"error": "Backend source not configured for this content."}, status=500)

    # Resolve body: prefer shared R2 cache (<1 day, reused across buyers),
    # fall back to this token's own ref, then local-dev file, then fresh fetch.
    from . import external_cache

    r2_configured = external_cache.is_configured()
    body = None
    content_length = 0
    r2_ref = None

    fresh_key = external_cache.get_fresh_key(content.id, source_url) if r2_configured else None
    if fresh_key:
        r2_ref = f"r2://{external_cache._bucket()}/{fresh_key}"
    elif external_cache.parse_r2_ref(dl.cached_file_path):
        # Token already points at shared cache — revalidate freshness.
        parsed = external_cache.parse_r2_ref(dl.cached_file_path)
        try:
            age = external_cache.key_age_days(external_cache._client(), parsed[0], parsed[1])
        except Exception:
            age = None
        if age is None or age > external_cache.CACHE_TTL_DAYS:
            dl.cached_file_path = ""
            dl.save(update_fields=["cached_file_path"])
        else:
            r2_ref = dl.cached_file_path

    if r2_ref:
        try:
            body, content_length, _ctype = external_cache.stream_ref(r2_ref)
            dl.cached_file_path = r2_ref
            dl.save(update_fields=["cached_file_path"])
        except Exception:
            logger.warning("Shared cache miss for content %s, refetching.", content.id)
            r2_ref, body = None, None

    local_path = None
    if body is None:
        if dl.cached_file_path and not dl.cached_file_path.startswith("r2://") and os.path.exists(dl.cached_file_path):
            local_path = dl.cached_file_path
        else:
            # Lazy fetch on first hit ( ONLY the first buyer per day pays this cost ).
            try:
                dest_name = f"ext_{dl.token[:16]}_{dl.content_id}"
                fetched = fetch_from_source(source_url, source_type, dest_name)
            except ValueError as exc:
                logger.warning("External fetch failed for content %s: %s", content.id, exc)
                return JsonResponse({"error": "Source file temporarily unavailable. Try again shortly."}, status=502)
            except Exception:  # noqa: BLE001 - never leak backend details
                logger.exception("External fetch crashed for content %s", content.id)
                return JsonResponse({"error": "Source file temporarily unavailable. Try again shortly."}, status=502)
            if r2_configured:
                try:
                    r2_ref = external_cache.upload_file(fetched, content.id, source_url)
                    try:
                        os.remove(fetched)
                    except OSError:
                        pass
                    dl.cached_file_path = r2_ref
                    dl.save(update_fields=["cached_file_path"])
                    body, content_length, _ctype = external_cache.stream_ref(r2_ref)
                except Exception:
                    logger.exception("R2 cache upload failed for content %s; serving local file.", content.id)
                    local_path = fetched
                    dl.cached_file_path = local_path
                    dl.save(update_fields=["cached_file_path"])
            else:
                local_path = fetched
                dl.cached_file_path = local_path
                dl.save(update_fields=["cached_file_path"])

    # Count use; expire when limit hit.
    dl.download_count += 1
    if dl.download_count >= dl.max_downloads:
        dl.is_expired = True
        dl.is_used = True
    dl.save(update_fields=["download_count", "is_expired", "is_used"])

    ext = "zip" if dl.content_type == "album" else "mp3"
    filename = f"{content.title}.{ext}"
    if body is not None:
        from django.http import StreamingHttpResponse

        size = 0

        def _iter():
            nonlocal size
            for chunk in body:
                size += len(chunk)
                yield chunk
            DownloadManager.mark_download_complete(dl, bytes_delivered=size or content_length)

        response = StreamingHttpResponse(_iter(), content_type="audio/mpeg")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        if content_length:
            response["Content-Length"] = str(content_length)
        dl.bytes_expected = content_length or None
        dl.save(update_fields=["bytes_expected"])
        return response

    try:
        DownloadManager.mark_download_complete(dl, bytes_delivered=os.path.getsize(local_path))
        return FileResponse(open(local_path, "rb"), as_attachment=True, filename=filename)
    except FileNotFoundError:
        dl.cached_file_path = ""
        dl.save(update_fields=["cached_file_path"])
        return JsonResponse({"error": "Cached file expired. Request a fresh link."}, status=410)
