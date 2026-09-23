from celery import shared_task
from .ad_revenue_service import credit_ad_revenue_to_djs
from .payout_processor import process_weekly_payouts as run_weekly_payouts


@shared_task
def credit_ad_revenue_task():
    """Weekly task to credit ad revenue share to DJs [Spec P3 §1.2]."""
    return credit_ad_revenue_to_djs()


@shared_task
def process_payouts_task():
    """Weekly task to process DJ payouts [Spec P2 §9]."""
    return run_weekly_payouts()


@shared_task
def process_weekly_payouts():
    """Alias for weekly automated payout processing."""
    return run_weekly_payouts()


@shared_task
def reset_monthly_quotas():
    """Placeholder for reset_monthly_quotas (quotas/subscriptions managed via payout_cron/etc)."""
    return "No-op: subscriptions handled via payout_cron."


@shared_task
def run_payout_cron():
    """Daily renewals + storage-overage billing (beat entry for payout_cron command)."""
    from django.core.management import call_command

    call_command("payout_cron")
    return "Payout cron completed."
