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

    content_type = allowed[ext]
    if kind != "cover":
        existing = find_unused_upload(kind, dj, stem, ext, size)
        if existing:  # same file already sitting in storage from an earlier try: reuse it, don't upload again
            return {"key": existing, "url": "", "headers": {}, "public_url": "", "existing": True}
    key = f"{key_prefix(kind, dj.id)}{uuid.uuid4().hex[:12]}-{stem}.{ext}"
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


def referenced_keys(dj):
    """Every file key this DJ's tracks and album packs point at (deleted ones included)."""
    from apps.albums.models import AlbumPack
    from apps.tracks.models import Track

    keys = set(Track.objects.filter(dj=dj).exclude(file_key="").values_list("file_key", flat=True))
    for fk, ok in AlbumPack.objects.filter(dj=dj).values_list("file_key", "original_file_key"):
        keys.update(k for k in (fk, ok) if k)
    try:
        from apps.albums.models import AlbumTrack

        keys.update(k for k in AlbumTrack.objects.filter(album__dj=dj).values_list("original_file_key", flat=True) if k)
    except Exception:
        pass
    try:  # files held in the Telegram vault keep their key too
        from apps.admin_panel.models import VaultFile

        keys.update(k for k in VaultFile.objects.exclude(file_key="").values_list("file_key", flat=True) if k.startswith(("tracks/", "albums/")))
    except Exception:
        pass
    return keys


def _list_prefix(kind, dj):
    out, token = [], None
    while True:
        kw = {"Bucket": bucket_for(kind), "Prefix": key_prefix(kind, dj.id), "MaxKeys": 1000}
        if token:
            kw["ContinuationToken"] = token
        page = client().list_objects_v2(**kw)
        out.extend(page.get("Contents") or [])
        if not page.get("IsTruncated"):
            return out
        token = page.get("NextContinuationToken")


def find_unused_upload(kind, dj, stem, ext, size):
    """An object this DJ already uploaded with the same name and size that no release uses yet."""
    try:
        used = referenced_keys(dj)
        for obj in _list_prefix(kind, dj):
            key = obj["Key"]
            if key not in used and int(obj.get("Size") or 0) == int(size) and key.endswith(f"-{stem}.{ext}"):
                return key
    except Exception:
        return None
    return None


def delete_orphans(kind, dj, older_than_hours=24):
    """Remove uploads no release points at (abandoned tries). Returns how many were deleted."""
    import datetime

    used = referenced_keys(dj)
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=older_than_hours)
    gone = 0
    for obj in _list_prefix(kind, dj):
        lm = obj.get("LastModified")
        if obj["Key"] not in used and lm is not None and lm < cutoff:
            client().delete_object(Bucket=bucket_for(kind), Key=obj["Key"])
            gone += 1
    return gone


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
