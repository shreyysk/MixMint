from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

def check_verification_eligibility(dj_profile):
    """
    Automated badge granting for top sellers [Imp 06].
    Requirements:
    - 50+ sales
    - ₹5,000+ total revenue
    - Account > 30 days old
    """
    if dj_profile.is_verified:
        return False
    
    # 1. Account age check
    if dj_profile.created_at > (timezone.now() - timedelta(days=30)):
        return False
    
    # 2. Sales check
    from apps.commerce.models import Purchase
    sales_count = Purchase.objects.filter(seller=dj_profile, status='paid').count()
    if sales_count < 50:
        return False
        
    # 3. Revenue check
    from apps.commerce.models import DJWallet
    wallet, _ = DJWallet.objects.get_or_create(dj=dj_profile)
    if wallet.total_earnings < Decimal("5000.00"):
        return False
        
    # Grant Badge
    dj_profile.is_verified = True
    dj_profile.verified_at = timezone.now()
    dj_profile.save()
    return True

def record_dj_page_view(dj_id, page_type, request=None):
    """Missing Item 02: Track storefront/track views for Dynamic Ad Floor Pricing"""
    from apps.accounts.models import DJPageView
    ip_address = None
    if request:
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            ip_address = x_forwarded.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')

    # Optional: basic deduplication per IP per day could be added here,
    # but for raw views, simple creation is standard.
    DJPageView.objects.create(
        dj_id=dj_id,
        page_type=page_type,
        ip_address=ip_address
    )
