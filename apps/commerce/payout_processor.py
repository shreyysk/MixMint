"""
MixMint Weekly Payout Processor [Spec P2 §9].

Handles:
- Weekly payout cycle processing
- ₹500 threshold enforcement
- Auto-retry on failed payouts
- Escrow chargeback protection
- Admin payout hold check
"""

from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.commerce.models import DJWallet, Payout, LedgerEntry


def process_weekly_payouts():
    """
    Process weekly payouts for all eligible DJs [Spec P2 §9].
    Called by Celery beat or cron job.

    Rules:
    - ₹500 minimum threshold
    - Skip DJs with held payouts
    - Reserve escrow for chargeback protection
    - Auto-retry failed payouts (max 3 attempts)
    """
    min_threshold = Decimal(str(settings.MIN_PAYOUT_THRESHOLD))
    processed = 0
    failed = 0

    # Get all wallets with sufficient pending earnings
    eligible_wallets = DJWallet.objects.filter(
        pending_earnings__gte=min_threshold,
        dj__status='approved',
        dj__user__payout_frozen=False,  # [Missing Item 05]
    ).select_related('dj', 'dj__user')

    for wallet in eligible_wallets:
        # Skip if DJ has held payouts
        if Payout.objects.filter(dj=wallet.dj, status='held').exists():
            continue

        try:
            payout_amount = _process_single_payout(wallet)
            if payout_amount:
                processed += 1
        except Exception:
            failed += 1

    return {
        'processed': processed,
        'failed': failed,
        'timestamp': timezone.now().isoformat(),
    }


@transaction.atomic
def _process_single_payout(wallet):
    """Process a single DJ payout with escrow protection."""
    # Calculate payout amount (pending - escrow reserve)
    # Keep 5% in escrow for chargeback protection
    escrow_rate = Decimal('0.05')
    escrow_reserve = (wallet.pending_earnings * escrow_rate).quantize(Decimal('0.01'))
    payout_amount = wallet.pending_earnings - escrow_reserve

    if payout_amount < Decimal(str(settings.MIN_PAYOUT_THRESHOLD)):
        return None

    # Create payout record
    payout = Payout.objects.create(
        dj=wallet.dj,
        amount=payout_amount,
        status='pending',
    )

    # Update wallet
    from django.db.models import F
    wallet.pending_earnings = Decimal('0.00')
    wallet.available_for_payout = Decimal('0.00')
    wallet.escrow_amount = F('escrow_amount') + escrow_reserve
    wallet.save(update_fields=['pending_earnings', 'available_for_payout', 'escrow_amount'])

    # Ledger entry for payout
    LedgerEntry.objects.create(
        wallet=wallet,
        amount=payout_amount,
        entry_type='debit',
        description=f'Weekly payout #{payout.id}',
        metadata={'payout_id': payout.id},
    )

    return payout_amount


def retry_failed_payouts(max_retries=3):
    """Auto-retry failed payouts [Spec P2 §9]."""
    failed_payouts = Payout.objects.filter(
        status='failed',
        auto_retry_count__lt=max_retries,
    )

    retried = 0
    for payout in failed_payouts:
        payout.status = 'pending'
        payout.auto_retry_count += 1
        payout.save()
        retried += 1

    return {'retried': retried}
