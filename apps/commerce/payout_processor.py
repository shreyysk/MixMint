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
    Weekly payout run [Spec P2 §9]. Pays each approved DJ their *available*
    (escrow-released) balance once it clears the ₹500 threshold.
    Skips frozen/banned accounts and DJs with a held payout.
    """
    min_threshold = Decimal(str(settings.MIN_PAYOUT_THRESHOLD))
    processed = 0
    failed = 0

    eligible_wallets = DJWallet.objects.filter(
        available_for_payout__gte=min_threshold,
        dj__status="approved",
        dj__is_deleted=False,
        dj__profile__is_frozen=False,
        dj__profile__is_banned=False,
    ).values_list("dj_id", flat=True)

    from datetime import timedelta

    week_ago = timezone.now() - timedelta(days=7)
    for dj_id in eligible_wallets:
        if Payout.objects.filter(dj_id=dj_id, status="held").exists():
            continue
        if Payout.objects.filter(dj_id=dj_id, created_at__gt=week_ago).exclude(status="failed").exists():
            continue  # already withdrew this week
        try:
            if _process_single_payout(dj_id):
                processed += 1
        except Exception:
            failed += 1

    return {
        "processed": processed,
        "failed": failed,
        "timestamp": timezone.now().isoformat(),
    }


def _process_single_payout(wallet_or_dj_id):
    """Pay out the DJ's available balance. Row-locked, so concurrent requests cannot double-pay."""
    dj_id = getattr(wallet_or_dj_id, "dj_id", wallet_or_dj_id)
    with transaction.atomic():
        wallet = DJWallet.objects.select_for_update().get(dj_id=dj_id)
        payout_amount = wallet.available_for_payout
        if payout_amount < Decimal(str(settings.MIN_PAYOUT_THRESHOLD)):
            return None

        payout = Payout.objects.create(dj_id=dj_id, amount=payout_amount, status="pending")
        wallet.available_for_payout = Decimal("0.00")
        wallet.pending_earnings -= payout_amount
        wallet.save(update_fields=["available_for_payout", "pending_earnings", "updated_at"])

        LedgerEntry.objects.create(
            wallet=wallet,
            amount=payout_amount,
            entry_type="debit",
            description=f"Payout #{payout.id}",
            metadata={"payout_id": payout.id, "type": "payout"},
        )
        transaction.on_commit(lambda: _notify_payout(payout))
    return payout_amount


def _notify_payout(payout):
    try:
        from apps.admin_panel.telegram import notify_admins

        notify_admins(f"💸 Payout #{payout.id}: ₹{payout.amount} to {payout.dj.dj_name}. Send it, then mark it paid in Admin → Payouts.")
    except Exception:
        pass
    try:
        from apps.core.email_service import EmailService

        EmailService.send_payout_initiated(payout.dj, payout)
    except Exception:  # an email problem must never undo a payout
        import logging

        logging.getLogger("mixmint").exception("Payout email failed for payout %s", payout.id)


def retry_failed_payouts(max_retries=3):
    """Auto-retry failed payouts [Spec P2 §9]."""
    failed_payouts = Payout.objects.filter(
        status="failed",
        auto_retry_count__lt=max_retries,
    )

    retried = 0
    for payout in failed_payouts:
        payout.status = "pending"
        payout.auto_retry_count += 1
        payout.save()
        retried += 1

    return {"retried": retried}
