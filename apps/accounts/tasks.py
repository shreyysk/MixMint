from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import Profile, LoginHistory
from apps.commerce.models import Payout
from apps.commerce.payout_processor import retry_failed_payouts, process_weekly_payouts

@shared_task
def expire_inactive_accounts():
    """
    Expire accounts with 12 months of inactivity [Spec §10].
    """
    twelve_months_ago = timezone.now() - timedelta(days=365)
    
    # Find profiles whose last login was more than 12 months ago
    inactive_profiles = Profile.objects.filter(
        user__last_login__lt=twelve_months_ago,
        is_frozen=False
    )
    
    count = inactive_profiles.update(is_frozen=True)
    return f"Expired {count} inactive accounts."

@shared_task
def run_weekly_payout_cycle():
    """Automated weekly payout processing [Spec P2 §9]."""
    return process_weekly_payouts()

@shared_task
def run_payout_retry_cycle():
    """Automated retry for failed payouts [Spec P2 §9]."""
    return retry_failed_payouts(max_retries=3)

@shared_task
def update_dj_popularity_scores():
    """
    Update DJ popularity scores based on sales and delivery [Spec §3.2].
    Algorithm: (Sales count last 30d * 5) + (Delivered downloads last 30d * 1)
    """
    thirty_days_ago = timezone.now() - timedelta(days=30)
    djs = DJProfile.objects.filter(status='approved')
    
    from django.db.models import Count, Q
    from apps.commerce.models import Purchase
    
    updated_count = 0
    for dj in djs:
        # Get successful sales in last 30d
        sales_count = Purchase.objects.filter(
            seller=dj,
            is_completed=True,
            created_at__gte=thirty_days_ago
        ).count()
        
        # Get successful deliveries in last 30d
        delivery_count = Purchase.objects.filter(
            seller=dj,
            download_completed=True,
            created_at__gte=thirty_days_ago
        ).count()
        
        new_score = (sales_count * 5) + (delivery_count * 1)
        if dj.popularity_score != new_score:
            dj.popularity_score = new_score
            dj.save(update_fields=['popularity_score'])
            updated_count += 1
            
    return f"Updated scores for {updated_count} DJs."
