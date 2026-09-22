"""
Shared R2 cache for external-source downloads (DJ Drive/MediaFire -> R2 -> buyer).

Why R2 (not local disk):
- Railway workers have ephemeral disk; a local file cached by worker A is
  invisible to worker B. R2 is shared across all workers.
- 1-day retention: the FIRST buyer pays the fetch cost; later buyers of the
  same track stream straight from R2 with zero Drive hits.
- Keyed by track + hash(source_url): if the DJ changes the backend link,
  a new cache object is created automatically.

Lifecycle: fetch-on-first-request -> upload to R2 private bucket under
`external_cache/` -> stream to buyer from R2 -> cleanup task deletes objects
older than 1 day. Local disk is only a dev fallback (no R2 creds).
"""

import hashlib
import logging
import os
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("mixmint")

CACHE_PREFIX = "external_cache/"
CACHE_TTL_DAYS = 2  # shared reuse window: next buyers stream from R2 for 2 days


def is_configured():
    """True when real R2 creds exist (dummy test creds / example endpoint = False)."""
    endpoint = getattr(settings, "AWS_S3_ENDPOINT_URL", "") or ""
    key = getattr(settings, "AWS_ACCESS_KEY_ID", "") or ""
    secret = getattr(settings, "AWS_SECRET_ACCESS_KEY", "") or ""
    bucket = getattr(settings, "R2_PRIVATE_BUCKET", "") or ""
    if not (endpoint and key and secret and bucket):
        return False
    if "example.invalid" in endpoint or key == "test":
        return False
    return True


def _client():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def _bucket():
    return getattr(settings, "R2_PRIVATE_BUCKET", "") or getattr(settings, "AWS_STORAGE_BUCKET_NAME", "")


def cache_key_for(track_id, source_url):
    digest = hashlib.sha256((source_url or "").encode()).hexdigest()[:16]
    return f"{CACHE_PREFIX}track_{track_id}/{digest}.bin"


def key_age_days(s3, bucket, key):
    """Age of a cached object in days; None if missing."""
    try:
        head = s3.head_object(Bucket=bucket, Key=key)
        last = head.get("LastModified")
        if not last:
            return None
        if timezone.is_naive(last):
            last = timezone.make_aware(last, timezone.utc)
        return (timezone.now() - last).total_seconds() / 86400.0
    except Exception:
        return None


def get_fresh_key(track_id, source_url):
    """Return cache key if a fresh (<1 day) object exists, else None."""
    if not is_configured():
        return None
    key = cache_key_for(track_id, source_url)
    try:
        age = key_age_days(_client(), _bucket(), key)
    except Exception:
        return None
    if age is None or age > CACHE_TTL_DAYS:
        return None
    return key


def upload_file(local_path, track_id, source_url, content_type="audio/mpeg"):
    """Upload fetched file to shared R2 cache. Returns 'r2://bucket/key'."""
    key = cache_key_for(track_id, source_url)
    s3 = _client()
    bucket = _bucket()
    s3.upload_file(
        local_path,
        bucket,
        key,
        ExtraArgs={"ContentType": content_type, "Metadata": {"cached-at": timezone.now().isoformat()}},
    )
    return f"r2://{bucket}/{key}"


def parse_r2_ref(ref):
    """'r2://bucket/key' -> (bucket, key); None if not an R2 ref."""
    if not ref or not ref.startswith("r2://"):
        return None
    rest = ref[len("r2://") :]  # noqa: E203 (black slice style)
    bucket, _, key = rest.partition("/")
    if not bucket or not key:
        return None
    return bucket, key


def stream_ref(ref, chunk_size=1024 * 256):
    """Yield (iterator, content_length, content_type) for an r2:// ref."""
    parsed = parse_r2_ref(ref)
    if not parsed:
        raise ValueR2Error("Not an R2 cache reference.")
    bucket, key = parsed
    s3 = _client()
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"], obj.get("ContentLength", 0), obj.get("ContentType", "application/octet-stream")


class ValueR2Error(ValueError):
    pass


def cleanup_old_cache(max_age_days=CACHE_TTL_DAYS):
    """Delete external_cache/ objects older than max_age_days. Returns count.

    Always sweeps local-dev temp files; R2 purge only when configured.
    """
    removed = 0
    # 1. Local-dev temp files for stale tokens (always safe).
    try:
        from .models import DownloadToken as DT

        for dl in DT.objects.exclude(cached_file_path="").exclude(cached_file_path__startswith="r2://")[:500]:
            path = dl.cached_file_path
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    removed += 1
                except OSError:
                    pass
            dl.cached_file_path = ""
            dl.save(update_fields=["cached_file_path"])
    except Exception:
        logger.exception("Local cache sweep failed.")
    # 2. Shared R2 objects older than TTL.
    if not is_configured():
        return removed
    s3 = _client()
    bucket = _bucket()
    cutoff = timezone.now() - timedelta(days=max_age_days)
    token = None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": CACHE_PREFIX, "MaxKeys": 1000}
        if token:
            kwargs["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kwargs)
        for item in resp.get("Contents", []):
            last = item.get("LastModified")
            if last and last.replace(tzinfo=None) < cutoff.replace(tzinfo=None):
                try:
                    s3.delete_object(Bucket=bucket, Key=item["Key"])
                    removed += 1
                except Exception:
                    logger.warning("Could not delete stale cache object %s", item["Key"])
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    # Clear dangling refs on tokens pointing at deleted/purged keys.
    try:
        from .models import DownloadToken

        (
            DownloadToken.objects.filter(cached_file_path__startswith="r2://")
            .exclude(cached_file_path="")
            .update(cached_file_path="")
            if removed
            else None
        )
    except Exception:
        pass
    return removed
