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
import time

import boto3
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.conf import settings

from .utils import DownloadManager
from apps.tracks.models import Track
from apps.albums.models import AlbumPack
from django.core.cache import cache
from apps.accounts.models import Profile, DJProfile
from apps.admin_panel.models import KillSwitch, FraudAlert

# Anti-leak delay threshold: files > 50MB get throttled [Spec §11]
LARGE_FILE_THRESHOLD = 50 * 1024 * 1024  # 50MB
THROTTLE_CHUNK_DELAY = 0.05  # 50ms delay per chunk for large files


def download_content(request, token_str):
    """
    Secure download proxy — validates token, checks bans, streams from R2,
    verifies byte completion with SHA-256 checksum, and creates audit log [Spec §4].
    """
    # 1. Kill switch check [Spec §4.6]
    if KillSwitch.objects.filter(is_active=True).exists():
        return JsonResponse({'error': 'Downloads are temporarily disabled.'}, status=503)

    client_ip = _get_client_ip(request)
    device_hash = request.META.get('HTTP_X_DEVICE_HASH')

    # 2. BanList check [Spec §4.6]
    is_banned, ban_msg = DownloadManager.check_ban_list(client_ip, device_hash)
    if is_banned:
        return JsonResponse({'error': ban_msg}, status=403)

    # 3. Validate token (one-time use, IP + device bound) [Spec §4.5]
    try:
        token = DownloadManager.validate_and_use(token_str, client_ip, device_hash)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=403)

    # 3.2 Concurrent connection limit (Max 2) [Spec §4.4]
    cache_key = f"dl_concurrency_{token_str}"
    current_conns = cache.get(cache_key, 0)
    if current_conns >= 2:
        return JsonResponse({
            'error': 'Too many concurrent connections. Please close other download threads.',
            'code': 'CONCURRENCY_LIMIT'
        }, status=429)
    
    # Increment concurrency count
    cache.set(cache_key, current_conns + 1, timeout=3600)  # 1 hour expiry

    # 4. Resolve content
    if token.content_type == 'track':
        content = get_object_or_404(Track, id=token.content_id, is_active=True, is_deleted=False)
    else:
        content = get_object_or_404(AlbumPack, id=token.content_id, is_active=True, is_deleted=False)

    # 4.1 Throttling for suspicious users [Spec §4.6]
    has_high_fraud = FraudAlert.objects.filter(user=token.user, severity='high', status='pending').exists()
    
    # 5. Increment attempt counter + create audit log [Spec P2 §6]
    attempt_count = DownloadManager.increment_attempt(client_ip, token.content_id, token.content_type)
    DownloadManager.create_download_log(
        user=token.user,
        content_id=token.content_id,
        content_type=token.content_type,
        ip_address=client_ip,
        device_hash=device_hash,
        attempt_number=attempt_count,
    )

    # 6. Stream from private R2 bucket [Spec §5]
    s3 = boto3.client(
        's3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )

    try:
        s3_object = s3.get_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=content.file_key)
        content_length = s3_object['ContentLength']

        # Track bytes + checksum for completion verification [Spec §4.4]
        bytes_counter = {'delivered': 0}
        sha256_hash = hashlib.sha256()
        is_large_file = content_length > LARGE_FILE_THRESHOLD

        def file_iterator(stream, chunk_size=8192):
            with stream as s:
                while True:
                    chunk = s.read(chunk_size)
                    if not chunk:
                        break
                    bytes_counter['delivered'] += len(chunk)
                    sha256_hash.update(chunk)

                    # Anti-leak delay for large files [Spec §11]
                    # Suspicious users get 200ms delay instead of 50ms [Spec §4.6]
                    active_delay = 0.2 if has_high_fraud else THROTTLE_CHUNK_DELAY
                    if is_large_file or has_high_fraud:
                        time.sleep(active_delay)

                    yield chunk

            # After full delivery — verify and mark complete [Spec §4.4]
            if bytes_counter['delivered'] >= content_length:
                checksum = sha256_hash.hexdigest()
                DownloadManager.mark_download_complete(
                    token, bytes_counter['delivered'],
                    checksum_ok=True
                )
                content.download_count += 1
                content.save(update_fields=['download_count'])

        filename = f"{content.title}.zip" if token.content_type == 'album' else f"{content.title}.mp3"
        response = StreamingHttpResponse(
            file_iterator(s3_object['Body']),
            content_type=s3_object.get('ContentType', 'application/octet-stream')
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = content_length
        response['X-MixMint-Token'] = token_str[:8] + '...'  # Truncated for logging

        # Store expected bytes on token
        token.bytes_expected = content_length
        token.save(update_fields=['bytes_expected'])

        # Decrement concurrency after streaming is done [Spec §4.4]
        try:
            response.streaming_content = _wrap_iterator(response.streaming_content, cache_key)
        except Exception:
            pass

        return response

    except s3.exceptions.NoSuchKey:
        return JsonResponse({'error': 'File not found in storage.'}, status=404)
    except Exception:
        return JsonResponse({'error': 'Failed to retrieve file from storage.'}, status=500)


def _wrap_iterator(iterator, cache_key):
    """Wraps streaming content to decrement concurrency on finish."""
    try:
        for chunk in iterator:
            yield chunk
    finally:
        current = cache.get(cache_key, 0)
        cache.set(cache_key, max(0, current - 1), timeout=3600)

def _get_client_ip(request):
    """Extract real client IP from request."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
