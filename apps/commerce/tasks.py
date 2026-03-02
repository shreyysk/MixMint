from celery import shared_task
from .ad_revenue_service import credit_ad_revenue_to_djs
from .payout_processor import process_weekly_payouts

@shared_task
def credit_ad_revenue_task():
    """Weekly task to credit ad revenue share to DJs [Spec P3 §1.2]."""
    return credit_ad_revenue_to_djs()

@shared_task
def process_payouts_task():
    """Weekly task to process DJ payouts [Spec P2 §9]."""
    return process_weekly_payouts()
