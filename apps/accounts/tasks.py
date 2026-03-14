from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import Profile, DJProfile
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
    
    from apps.commerce.models import Purchase
    
    updated_count = 0
    for dj in djs:
        # Get successful sales in last 30d
        sales_count = Purchase.objects.filter(
            seller=dj,
            status='paid',
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

@shared_task
def calculate_storage_overages():
    """
    Calculate storage overages for Pro DJs [Spec P3 §1.5].
    20GB base. ₹59 per 5GB tier.
    """
    from apps.tracks.models import Track
    from apps.commerce.models import StorageOverage
    from django.db.models import Sum
    
    pro_profiles = Profile.objects.filter(is_pro_dj=True)
    today = timezone.now().date()
    first_of_month = today.replace(day=1)
    
    for profile in pro_profiles:
        try:
            dj_profile = profile.dj_profile
        except DJProfile.DoesNotExist:
            continue
            
        # Calculate usage [Gap 01: Storage Tracking]
        total_bytes = Track.objects.filter(dj=dj_profile).aggregate(total=Sum('file_size'))['total'] or 0
        quota_bytes = (dj_profile.custom_storage_quota_mb or profile.storage_quota_mb or 20480) * 1024 * 1024
        
        if total_bytes > quota_bytes:
            overage_bytes = total_bytes - quota_bytes
            # Calculate tiers (5GB per tier = ₹59)
            tier_size = 5 * 1024 * 1024 * 1024
            tiers = (overage_bytes + tier_size - 1) // tier_size
            amount_paise = int(tiers * 59 * 100)
            
            # Create or update overage record for this month
            StorageOverage.objects.update_or_create(
                dj=dj_profile,
                billing_month=first_of_month,
                defaults={
                    'usage_bytes': total_bytes,
                    'overage_bytes': overage_bytes,
                    'amount_paise': amount_paise,
                    'status': 'pending'
                }
            )
            
    return f"Calculated overages for {pro_profiles.count()} Pro DJs."
