"""
MixMint Account Lifecycle Management [Spec §11, §13].

Handles:
- Inactive account auto-expiry after 12 months
- Account cleanup notifications
"""

from datetime import timedelta
from django.utils import timezone

from apps.accounts.models import User, Profile


def expire_inactive_accounts():
    """
    Auto-expire accounts inactive for 12 months [Spec §13].
    Called by Celery beat or cron job.

    Process:
    1. Find accounts with last_active_at > 12 months ago
    2. Mark as inactive (don't delete — data retention)
    """
    cutoff = timezone.now() - timedelta(days=365)

    # Find inactive profiles
    inactive_profiles = Profile.objects.filter(
        last_active_at__lt=cutoff,
        is_banned=False,
        is_frozen=False,
    )

    expired_count = 0
    for profile in inactive_profiles:
        # Mark user as inactive
        profile.user.is_active = False
        profile.user.save(update_fields=['is_active'])
        expired_count += 1

    return {
        'expired_count': expired_count,
        'cutoff_date': cutoff.isoformat(),
    }


def update_last_active(user):
    """Update last_active_at on user activity."""
    try:
        profile = user.profile
        profile.last_active_at = timezone.now()
        profile.save(update_fields=['last_active_at'])
    except Profile.DoesNotExist:
        pass
