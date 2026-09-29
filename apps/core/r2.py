"""
Cloudflare R2 helpers (S3 API).

Uploads go straight from the DJ's browser to R2 with a short-lived signed PUT URL,
because a serverless function (Vercel) only accepts request bodies of a few MB.

    browser --(1) ask for upload URL--> Django   (checks: approved DJ, file type, size, quota)
    browser --(2) PUT file----------->  R2        (signed URL, 1 hour)
    browser --(3) save form---------->  Django   (checks the object really exists in R2)

One-time R2 setup (bucket CORS) is described in docs/R2_UPLOADS.md.
"""

import re
import uuid

from django.conf import settings

AUDIO_EXT = {"mp3": "audio/mpeg", "wav": "audio/wav", "flac": "audio/flac", "aiff": "audio/aiff", "aif": "audio/aiff"}
ZIP_EXT = {"zip": "application/zip"}
IMAGE_EXT = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}

KINDS = {
    # kind: (allowed extensions, bucket setting, max MB setting/default, key prefix)
    "audio": (AUDIO_EXT, "R2_PRIVATE_BUCKET", "MAX_UPLOAD_SIZE_MB", "tracks"),
    "album": (ZIP_EXT, "R2_PRIVATE_BUCKET", "MAX_ALBUM_UPLOAD_SIZE_MB", "albums"),
    "cover": (IMAGE_EXT, "R2_PUBLIC_BUCKET", "MAX_COVER_SIZE_MB", "covers"),
}
DEFAULT_MAX_MB = {"MAX_UPLOAD_SIZE_MB": 200, "MAX_ALBUM_UPLOAD_SIZE_MB": 1024, "MAX_COVER_SIZE_MB": 10}


class UploadError(ValueError):
    pass


def configured():
    return bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY and settings.AWS_S3_ENDPOINT_URL)


def client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def bucket_for(kind):
    return getattr(settings, KINDS[kind][1])


def max_bytes(kind):
    name = KINDS[kind][2]
    return int(getattr(settings, name, DEFAULT_MAX_MB[name])) * 1024 * 1024


def public_url(key):
    base = (getattr(settings, "R2_PUBLIC_URL", "") or "").rstrip("/")
    if not base:
        domain = getattr(settings, "AWS_S3_CUSTOM_DOMAIN", "")
        base = f"https://{domain}" if domain else ""
    return f"{base}/{key}" if base else ""


def key_prefix(kind, dj_id):
    return f"{KINDS[kind][3]}/{dj_id}/"


def _safe_name(filename):
    stem, _, ext = (filename or "file").rpartition(".")
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem or "file").strip("-.")[:60] or "file"
    return stem, ext.lower()


def presign_upload(kind, dj, filename, size):
    """Validate an upload request and return {key, url, headers, public_url}."""
    if kind not in KINDS:
        raise UploadError("Unknown upload type.")
    if not configured():
        raise UploadError("File storage isn't set up yet. Ask the admin to add the R2 keys.")
    allowed = KINDS[kind][0]
    stem, ext = _safe_name(filename)
    if ext not in allowed:
        raise UploadError(f"Please choose a {', '.join(sorted(e.upper() for e in allowed))} file.")
    try:
        size = int(size)
    except (TypeError, ValueError):
        raise UploadError("Could not read the file size.")
    if size <= 0:
        raise UploadError("That file is empty.")
    limit = max_bytes(kind)
    if size > limit:
        raise UploadError(f"That file is too big (max {limit // (1024 * 1024)} MB).")
    if kind != "cover":
        quota_mb = dj.profile.storage_quota_mb or 0
        used = _used_bytes(dj)
        if quota_mb and used + size > quota_mb * 1024 * 1024:
            raise UploadError(
                f"Not enough storage left ({(quota_mb * 1024 * 1024 - used) // (1024 * 1024)} MB free). "
                "Delete old uploads or upgrade to Pro."
            )
    if kind == "cover" and not public_url("x"):
        raise UploadError("Cover uploads need R2_PUBLIC_URL to be set. You can skip the cover for now.")

    key = f"{key_prefix(kind, dj.id)}{uuid.uuid4().hex[:12]}-{stem}.{ext}"
    content_type = allowed[ext]
    url = client().generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket_for(kind), "Key": key, "ContentType": content_type},
        ExpiresIn=3600,
    )
    return {
        "key": key,
        "url": url,
        "headers": {"Content-Type": content_type},
        "public_url": public_url(key) if kind == "cover" else "",
    }


def uploaded_size(kind, dj, key):
    """Size of an object the DJ says they uploaded, or raise UploadError."""
    if not key or not key.startswith(key_prefix(kind, dj.id)) or ".." in key:
        raise UploadError("Upload not found. Please choose the file again.")
    try:
        head = client().head_object(Bucket=bucket_for(kind), Key=key)
    except Exception:
        raise UploadError("The upload didn't finish. Please try again.")
    return int(head.get("ContentLength") or 0)


def cover_key_from_url(url, dj):
    """Accept a cover URL only if it points at this DJ's folder in our public bucket."""
    if not url:
        return ""
    base = public_url("")
    if not base or not url.startswith(base):
        raise UploadError("Invalid cover image.")
    key = url[len(base):]
    uploaded_size("cover", dj, key)
    return key


def _used_bytes(dj):
    from django.db.models import Sum

    from apps.albums.models import AlbumPack
    from apps.tracks.models import Track

    t = Track.objects.filter(dj=dj, is_deleted=False).aggregate(s=Sum("file_size"))["s"] or 0
    a = AlbumPack.objects.filter(dj=dj, is_deleted=False).aggregate(s=Sum("file_size"))["s"] or 0
    return t + a
