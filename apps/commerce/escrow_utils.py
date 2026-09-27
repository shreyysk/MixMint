from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.db import models, transaction
from apps.commerce.models import Purchase, DJWallet, LedgerEntry


def release_escrow_funds():
    """
    Move sale credits from escrow to available_for_payout once the hold passes [Spec P2 §9].
    Verified DJs: 24h, everyone else: 48h. Idempotent (Purchase.is_escrow_released).
    """
    now = timezone.now()
    released_count = 0
    total_released = Decimal("0.00")

    candidates = Purchase.objects.filter(status="paid", is_escrow_released=False, is_revoked=False).filter(
        models.Q(seller__is_verified=True, paid_at__lte=now - timedelta(hours=24))
        | models.Q(seller__is_verified=False, paid_at__lte=now - timedelta(hours=48))
    )

    for purchase_id in candidates.values_list("id", flat=True):
        with transaction.atomic():
            purchase = Purchase.objects.select_for_update().get(pk=purchase_id)
            if purchase.is_escrow_released or purchase.is_revoked or purchase.status != "paid":
                continue
            credits = LedgerEntry.objects.filter(
                entry_type="credit", metadata__purchase_id=purchase.id, metadata__escrow=True
            )
            for entry in credits:
                wallet = DJWallet.objects.select_for_update().get(pk=entry.wallet_id)
                amount = entry.amount
                wallet.escrow_amount -= amount
                wallet.available_for_payout += amount
                wallet.save()
                LedgerEntry.objects.create(
                    wallet=wallet,
                    amount=amount,
                    entry_type="transfer",
                    description=f"Escrow release for purchase {purchase.id}",
                    metadata={"purchase_id": purchase.id, "action": "escrow_release"},
                )
                total_released += amount
            purchase.is_escrow_released = True
            purchase.save(update_fields=["is_escrow_released"])
            released_count += 1

        # Referral bonuses are paid on the referred DJ's first sale that has cleared
        # escrow (not at payment time), so refunded/self-dealt sales never trigger them.
        try:
            from apps.commerce.dj_conversion import DJReferralProgram

            DJReferralProgram.process_first_sale_bonus(purchase.seller)
        except Exception:
            import logging

            logging.getLogger("mixmint").exception("Referral bonus processing failed for DJ %s", purchase.seller_id)

    return released_count, total_released


def place_earnings_hold(dj_id, hold_type, amount=None, reason="", admin_id=None, notify_dj=True):
    """Missing Item 05: move withdrawable money into escrow under an admin hold."""
    from apps.commerce.models import EarningsHold, AdminAuditLog

    with transaction.atomic():
        DJWallet.objects.get_or_create(dj_id=dj_id)
        wallet = DJWallet.objects.select_for_update().get(dj_id=dj_id)
        hold_amount = Decimal(str(amount)) if amount is not None else wallet.available_for_payout
        if hold_amount <= 0:
            raise ValueError("Hold amount must be positive")
        if hold_amount > wallet.available_for_payout:
            raise ValueError("Hold amount exceeds available earnings")

        wallet.available_for_payout -= hold_amount
        wallet.escrow_amount += hold_amount
        wallet.save()

        hold = EarningsHold.objects.create(
            dj_id=dj_id,
            amount=int(hold_amount * 100),  # EarningsHold.amount is paise
            hold_type=hold_type,
            reason=reason,
            placed_by_id=admin_id,
            status="active",
        )
        AdminAuditLog.objects.create(
            admin_id=admin_id,
            action="place_earnings_hold",
            target_dj_id=dj_id,
            details={"amount": str(hold_amount), "type": hold_type, "reason": reason},
        )

    if notify_dj:
        try:
            from apps.admin_panel.email_utils import send_email
            from django.utils.html import escape

            send_email(
                to_email=wallet.dj.profile.user.email,
                subject="MixMint Earnings Hold Notice",
                html_content=(
                    f"<p>A hold of ₹{hold_amount} has been placed on your earnings for "
                    f"{escape(hold_type.replace('_', ' '))}. Please contact support for more details.</p>"
                ),
            )
        except Exception:
            pass
    return hold


def release_earnings_hold(hold_id, admin_id, outcome="released"):
    """Missing Item 05: release (back to available) or forfeit (removed) an earnings hold."""
    from apps.commerce.models import EarningsHold, AdminAuditLog

    if outcome not in ("released", "forfeited"):
        raise ValueError("outcome must be 'released' or 'forfeited'")

    with transaction.atomic():
        hold = EarningsHold.objects.select_for_update().get(id=hold_id, status="active")
        wallet = DJWallet.objects.select_for_update().get(dj_id=hold.dj_id)
        amount = Decimal(hold.amount) / 100

        wallet.escrow_amount -= amount
        if outcome == "released":
            wallet.available_for_payout += amount
        else:
            wallet.pending_earnings -= amount
            wallet.total_earnings -= amount
        wallet.save()

        hold.status = outcome
        hold.resolved_by_id = admin_id
        hold.resolved_at = timezone.now()
        hold.save()

        AdminAuditLog.objects.create(
            admin_id=admin_id,
            action=f"resolve_earnings_hold_{outcome}",
            target_dj_id=hold.dj_id,
            details={"hold_id": str(hold.id), "amount": str(amount)},
        )

    if outcome == "released":
        try:
            from apps.admin_panel.email_utils import send_email

            send_email(
                to_email=wallet.dj.profile.user.email,
                subject="MixMint Earnings Hold Released",
                html_content=f"<p>A hold of ₹{amount} on your earnings has been released.</p>",
            )
        except Exception:
            pass
    return hold
