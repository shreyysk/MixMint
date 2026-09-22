import logging

from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger("mixmint")


@shared_task
def cleanup_expired_tokens():
    """Daily task to clean up expired download tokens [BUG-14]."""
    call_command("cleanup_tokens")
    return "Expired tokens cleaned up successfully."


@shared_task
def cleanup_expired_downloads():
    """Purge shared R2 external cache older than 1 day + stale local temp files.

    Runs every 5-10 min via Celery beat. Never touches DJ source files or R2 originals.
    """
    from . import external_cache

    removed = external_cache.cleanup_old_cache(max_age_days=external_cache.CACHE_TTL_DAYS)
    return f"Cleaned {removed} cached external file(s)."
