"""
Canonical money movement for MixMint.

Wallet semantics (all amounts in rupees, Decimal):
    total_earnings        lifetime credited earnings
    pending_earnings      earned but not yet paid out  (= escrow + available)
    escrow_amount         held for the chargeback window or by an admin hold
    available_for_payout  released and withdrawable

A sale credits escrow; `release_escrow_funds` moves it to available after the
hold period; payouts debit available. Every movement writes a LedgerEntry.
"""

import logging
import secrets
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from apps.admin_panel.models import PlatformSettings, PromotionalOffer

from .models import DJWallet, Invoice, LedgerEntry, TaxRecord

logger = logging.getLogger("mixmint")

CENT = Decimal("0.01")
GST_RATE = Decimal("18.00")


def money(value):
    return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)


def _locked_wallet(dj_profile):
    DJWallet.objects.get_or_create(dj=dj_profile)
    return DJWallet.objects.select_for_update().get(dj=dj_profile)


def credit_wallet(dj_profile, amount, description, metadata=None, escrow=True):
    """Credit a DJ. escrow=True holds the money until the release job runs."""
    amount = money(amount)
    if amount <= 0:
        return None
    with transaction.atomic():
        wallet = _locked_wallet(dj_profile)
        wallet.total_earnings += amount
        wallet.pending_earnings += amount
        if escrow:
            wallet.escrow_amount += amount
        else:
            wallet.available_for_payout += amount
        wallet.save()
        meta = dict(metadata or {})
        meta["escrow"] = bool(escrow)
        return LedgerEntry.objects.create(
            wallet=wallet, amount=amount, entry_type="credit", description=description, metadata=meta
        )


class MonetizationService:
    @staticmethod
    def get_commission_rate(dj_profile):
        """Global rate; Pro DJs pay at most 8% unless a promo sets a lower global rate."""
        settings_obj = PlatformSettings.load()
        rate = Decimal(settings_obj.platform_commission_rate)
        if PromotionalOffer.objects.filter(is_active=True, dj__isnull=True).exists():
            return rate
        is_pro = bool(getattr(getattr(dj_profile, "profile", None), "is_pro_dj", False))
        if is_pro and rate > Decimal("8.00"):
            return Decimal("8.00")
        return rate

    @staticmethod
    def calculate_revenue_split(dj_profile, total_amount):
        commission_rate = MonetizationService.get_commission_rate(dj_profile)
        total_amount = money(total_amount)
        platform_amount = money(total_amount * commission_rate / Decimal("100"))
        return {
            "dj_amount": total_amount - platform_amount,
            "platform_amount": platform_amount,
            "commission_rate": commission_rate,
        }

    @staticmethod
    def _recipients(purchase, dj_total):
        """[(dj_profile, amount)] — collaborators by %, owner keeps the remainder."""
        recipients = []
        if purchase.content_type == "track":
            from apps.tracks.models import TrackCollaborator

            for collab in TrackCollaborator.objects.filter(track_id=purchase.content_id).select_related("dj"):
                if collab.dj_id == purchase.seller_id:
                    continue
                share = money(dj_total * Decimal(collab.revenue_percentage) / Decimal("100"))
                if share > 0:
                    recipients.append((collab.dj, share))
        assigned = sum((a for _, a in recipients), Decimal("0.00"))
        if assigned > dj_total:  # corrupt percentages: never pay out more than the DJ share
            recipients, assigned = [], Decimal("0.00")
        recipients.insert(0, (purchase.seller, dj_total - assigned))
        return recipients

    @staticmethod
    def generate_invoice(purchase):
        settings_obj = PlatformSettings.load()
        total_amount = money(purchase.price_paid)
        subtotal, tax_amount = total_amount, Decimal("0.00")
        if settings_obj.gst_charging_enabled:
            base = money(total_amount / (Decimal("1") + GST_RATE / Decimal("100")))
            tax_amount = total_amount - base
            subtotal = base
        invoice = Invoice.objects.create(
            purchase=purchase,
            user=purchase.user,
            dj=purchase.seller,
            invoice_number=f"INV-{timezone.now():%Y%m%d}-{secrets.token_hex(4).upper()}",
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            status="issued",
        )
        TaxRecord.objects.create(
            invoice=invoice, tax_type="GST", tax_rate=GST_RATE, tax_amount=tax_amount, jurisdiction="India"
        )
        return invoice

    @staticmethod
    def complete_purchase(purchase):
        """
        Post-payment processing, exactly once per purchase (row lock + invoice guard):
        revenue split -> escrow credits -> invoice -> verification badge check.
        """
        from .models import Purchase

        with transaction.atomic():
            locked = Purchase.objects.select_for_update().get(pk=purchase.pk)
            if locked.status != "paid" or Invoice.objects.filter(purchase=locked).exists():
                return locked

            # Buyer-side platform fee is platform revenue, never part of the DJ split.
            base = money(locked.price_paid) - money(locked.platform_fee)
            split = MonetizationService.calculate_revenue_split(locked.seller, base)
            locked.commission = split["platform_amount"]
            locked.dj_revenue = split["dj_amount"]
            locked.dj_earnings = split["dj_amount"]
            locked.save(update_fields=["commission", "dj_revenue", "dj_earnings"])

            for dj, amount in MonetizationService._recipients(locked, split["dj_amount"]):
                credit_wallet(
                    dj,
                    amount,
                    description=f"Sale of {locked.content_type} #{locked.content_id} (purchase {locked.id})",
                    metadata={
                        "purchase_id": locked.id,
                        "commission_rate": str(split["commission_rate"]),
                        "type": "sale",
                    },
                    escrow=True,
                )

            MonetizationService.generate_invoice(locked)

        try:
            from apps.accounts.utils import check_verification_eligibility

            check_verification_eligibility(locked.seller)
        except Exception:
            logger.exception("Verification check failed for DJ %s", locked.seller_id)
        return locked

    @staticmethod
    def reverse_purchase(purchase, reason="refund"):
        """Claw back every credit made for a purchase (refund / chargeback)."""
        from .models import Purchase

        with transaction.atomic():
            locked = Purchase.objects.select_for_update().get(pk=purchase.pk)
            credits = LedgerEntry.objects.filter(entry_type="credit", metadata__purchase_id=locked.id)
            already = LedgerEntry.objects.filter(
                entry_type="debit", metadata__purchase_id=locked.id, metadata__type="reversal"
            ).exists()
            if already:
                return 0
            reversed_total = Decimal("0.00")
            for entry in credits:
                wallet = DJWallet.objects.select_for_update().get(pk=entry.wallet_id)
                amt = money(entry.amount)
                wallet.total_earnings -= amt
                wallet.pending_earnings -= amt
                if locked.is_escrow_released:
                    wallet.available_for_payout -= amt  # may go negative = debt against future sales
                else:
                    wallet.escrow_amount -= amt
                wallet.save()
                LedgerEntry.objects.create(
                    wallet=wallet,
                    amount=amt,
                    entry_type="debit",
                    description=f"Reversal ({reason}) for purchase {locked.id}",
                    metadata={"purchase_id": locked.id, "type": "reversal", "reason": reason},
                )
                reversed_total += amt
            locked.is_revoked = True
            locked.save(update_fields=["is_revoked"])
            return reversed_total

    # Back-compat shim for older callers.
    @staticmethod
    def record_revenue(dj_profile, amount, sale_type, reference_id, track=None):
        split = MonetizationService.calculate_revenue_split(dj_profile, amount)
        credit_wallet(
            dj_profile,
            split["dj_amount"],
            description=f"Revenue from {sale_type} ({reference_id})",
            metadata={"reference_id": str(reference_id), "type": sale_type},
            escrow=True,
        )
        return split
