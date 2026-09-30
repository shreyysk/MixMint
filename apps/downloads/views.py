"""
MixMint Secure Download Proxy [Spec §4].

Handles:
- Token validation with IP + device binding
- Kill switch / maintenance mode checks
- Streaming from private R2 bucket
- SHA-256 checksum calculation during stream
- Byte completion verification
- Download speed throttle for suspicious users
- Anti-leak delay for large files
"""

import hashlib
import logging
import time

import boto3
from django.http import JsonResponse, StreamingHttpResponse
from django.utils.http import content_disposition_header
from django.conf import settings

from .models import DownloadToken
from .utils import DownloadManager
from apps.tracks.models import Track
from apps.albums.models import AlbumPack
from django.core.cache import cache
from apps.admin_panel.models import KillSwitch, FraudAlert

logger = logging.getLogger("mixmint")

CHUNK_SIZE = 256 * 1024  # 256 KB chunks
# Suspicious accounts only: ~2.5 MB/s instead of a hard stall (fits serverless time limits).
SUSPICIOUS_CHUNK_DELAY = 0.1


def _resolve_content(token):
    model = Track if token.content_type == "track" else AlbumPack
    return model.objects.filter(id=token.content_id, is_active=True, is_deleted=False).first()


def _filename(content, token):
    if token.content_type == "album":
        ext = "zip"
    else:
        ext = (content.file_key.rsplit(".", 1)[-1].lower() if "." in (content.file_key or "") else "") or "mp3"
    safe_title = "".join(c for c in content.title if c not in '\\/:*?"<>|\r\n').strip() or "download"
    return f"{safe_title}.{ext}"


def download_content(request, token_str):
    """
    Secure download proxy — validates token, checks bans, streams from R2,
    verifies byte completion with SHA-256 checksum, and creates audit log [Spec §4].
    """
    if KillSwitch.objects.filter(is_active=True).exists():
        return JsonResponse({"error": "Downloads are temporarily disabled."}, status=503)

    client_ip = _get_client_ip(request)
    device_hash = request.META.get("HTTP_X_DEVICE_HASH")

    is_banned, ban_msg = DownloadManager.check_ban_list(client_ip, device_hash)
    if is_banned:
        return JsonResponse({"error": ban_msg}, status=403)

    # Tokens are personal: when a session is present it must be the owner's.
    if request.user.is_authenticated:
        owner_ok = DownloadToken.objects.filter(token=token_str, user__user=request.user).exists()
        if not owner_ok and DownloadToken.objects.filter(token=token_str).exists():
            return JsonResponse({"error": "This download link belongs to another account."}, status=403)

    try:
        token = DownloadManager.validate_and_use(token_str, client_ip, device_hash)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=403)

    if token.user.is_frozen or token.user.is_banned:
        return JsonResponse({"error": "Your account is restricted. Contact support."}, status=403)

    content = _resolve_content(token)
    if content is None:
        return JsonResponse({"error": "This item is no longer available."}, status=404)
    if not content.file_key:
        # External-source item: hand over to the external flow with a fresh token.
        return JsonResponse(
            {"error": "This item is delivered from the DJ's source. Use the download button again.", "external": True},
            status=409,
        )

    # Concurrent connection limit per user (max 2) [Spec §4.4]
    cache_key = f"dl_concurrency_{token.user_id}"
    cache.add(cache_key, 0, timeout=3600)
    try:
        current_conns = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=3600)
        current_conns = 1
    if current_conns > 2:
        _release_slot(cache_key)
        return JsonResponse(
            {"error": "Too many concurrent downloads. Please wait for one to finish.", "code": "CONCURRENCY_LIMIT"},
            status=429,
        )

    has_high_fraud = FraudAlert.objects.filter(user=token.user, severity="high", status="pending").exists()

    delivery = getattr(settings, "DOWNLOAD_DELIVERY", "proxy")
    if delivery in ("auto", "presigned") and not has_high_fraud:
        handed_off = _presigned_handoff(request, token, content, cache_key, client_ip, device_hash, delivery)
        if handed_off is not None:
            return handed_off

    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        try:
            s3_object = s3.get_object(Bucket=settings.R2_PRIVATE_BUCKET, Key=content.file_key)
        except Exception as missing:
            # Missing in R2? Put it back from the Telegram vault copy, then serve as usual.
            from apps.admin_panel.vault import restore

            if not restore(token.content_type, content):
                raise missing
            s3_object = s3.get_object(Bucket=settings.R2_PRIVATE_BUCKET, Key=content.file_key)
    except Exception as exc:
        _release_slot(cache_key)
        # Give the attempt back: a storage failure is not the buyer's fault.
        DownloadToken.objects.filter(pk=token.pk).update(is_used=False)
        from botocore.exceptions import ClientError

        code = exc.response.get("Error", {}).get("Code") if isinstance(exc, ClientError) else None
        if code in ("NoSuchKey", "404"):
            logger.error("Missing R2 object for %s %s: %s", token.content_type, content.id, content.file_key)
            return JsonResponse({"error": "File not found in storage. Support has been notified."}, status=404)
        logger.exception("R2 fetch failed for %s %s", token.content_type, content.id)
        return JsonResponse({"error": "Storage is temporarily unavailable. Please retry."}, status=503)

    attempt_count = DownloadManager.increment_attempt(client_ip, token.content_id, token.content_type, user=token.user)
    DownloadManager.create_download_log(
        user=token.user,
        content_id=token.content_id,
        content_type=token.content_type,
        ip_address=client_ip,
        device_hash=device_hash,
        attempt_number=attempt_count,
    )

    content_length = s3_object["ContentLength"]
    bytes_counter = {"delivered": 0}
    sha256_hash = hashlib.sha256()

    def file_iterator(stream, chunk_size=CHUNK_SIZE):
        try:
            with stream as s:
                while True:
                    chunk = s.read(chunk_size)
                    if not chunk:
                        break
                    bytes_counter["delivered"] += len(chunk)
                    sha256_hash.update(chunk)
                    # Only accounts under a pending high-severity fraud alert are slowed down [Spec §4.6].
                    if has_high_fraud:
                        time.sleep(SUSPICIOUS_CHUNK_DELAY)
                    yield chunk

            if bytes_counter["delivered"] == content_length:
                checksum = sha256_hash.hexdigest()
                is_valid = not getattr(content, "checksum", None) or checksum == content.checksum
                DownloadManager.mark_download_complete(
                    token, bytes_delivered=bytes_counter["delivered"], checksum_hex=checksum, checksum_ok=is_valid
                )
                if is_valid:
                    from django.db.models import F

                    type(content).objects.filter(pk=content.pk).update(download_count=F("download_count") + 1)
        finally:
            _release_slot(cache_key)

    response = StreamingHttpResponse(
        file_iterator(s3_object["Body"]), content_type=s3_object.get("ContentType") or "application/octet-stream"
    )
    response["Content-Disposition"] = content_disposition_header(True, _filename(content, token))
    response["Content-Length"] = content_length
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"

    token.bytes_expected = content_length
    token.save(update_fields=["bytes_expected"])
    return response


def _r2_client():
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name="auto",  # Cloudflare R2
        config=Config(signature_version="s3v4"),
    )


def _presigned_handoff(request, token, content, cache_key, client_ip, device_hash, delivery):
    """
    Redirect to a short-lived R2 signed URL (after every token/ban/owner check above).
    Used for large files on serverless hosts, where streaming through the function could be
    cut off by its time or size limit. Returns None to fall back to the streaming proxy.
    Completion is recorded at hand-off (R2 serves the exact stored object); the byte-verified
    proxy stays in use for small files and for accounts under a fraud alert.
    """
    from django.http import HttpResponseRedirect

    try:
        s3 = _r2_client()
        head = s3.head_object(Bucket=settings.R2_PRIVATE_BUCKET, Key=content.file_key)
        size = int(head.get("ContentLength") or 0)
        if delivery == "auto" and size <= settings.DOWNLOAD_PROXY_MAX_MB * 1024 * 1024:
            return None
        url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.R2_PRIVATE_BUCKET,
                "Key": content.file_key,
                "ResponseContentDisposition": content_disposition_header(True, _filename(content, token)),
                "ResponseCacheControl": "private, no-store",
            },
            ExpiresIn=settings.DOWNLOAD_PRESIGN_SECONDS,
        )
    except Exception:
        logger.exception("Signed-URL hand-off failed for %s %s; using proxy.", token.content_type, content.id)
        return None

    attempt = DownloadManager.increment_attempt(client_ip, token.content_id, token.content_type, user=token.user)
    DownloadManager.create_download_log(
        user=token.user,
        content_id=token.content_id,
        content_type=token.content_type,
        ip_address=client_ip,
        device_hash=device_hash,
        attempt_number=attempt,
    )
    token.bytes_expected = size
    token.save(update_fields=["bytes_expected"])
    DownloadManager.mark_download_complete(
        token, bytes_delivered=size, checksum_hex=getattr(content, "checksum", None), checksum_ok=True
    )
    from django.db.models import F

    type(content).objects.filter(pk=content.pk).update(download_count=F("download_count") + 1)
    _release_slot(cache_key)
    response = HttpResponseRedirect(url)
    response["Cache-Control"] = "private, no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response


def _release_slot(cache_key):
    try:
        if cache.decr(cache_key) < 0:
            cache.set(cache_key, 0, timeout=3600)
    except ValueError:
        pass


def _get_client_ip(request):
    """Extract real client IP from request."""
    from apps.core.net import get_client_ip

    return get_client_ip(request)
