from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from apps.commerce.models import Purchase, DJWallet, LedgerEntry

def release_escrow_funds():
    """
    Release funds from escrow to available_for_payout [Spec P2 §9].
    - Verified DJs: 24h release
    - Standard DJs: 48h release
    
    This should be run periodically (e.g., hourly).
    """
    now = timezone.now()
    records_processed = 0
    total_released = Decimal('0.00')

    # Find purchases that are completed but haven't had their escrow released
    # We use a custom metadata field in LedgerEntry or a new field in Purchase to track release
    # For simplicity, we'll look for purchases where 'paid_at' is past the hold period
    
    # 1. Verified DJs (24h)
    verified_cutoff = now - timedelta(hours=24)
    purchases_to_release_verified = Purchase.objects.filter(
        status='paid',
        paid_at__lte=verified_cutoff,
        seller__is_verified=True,
        is_escrow_released=False # Need to add this field or track via Ledger
    )

    # 2. Standard DJs (48h)
    standard_cutoff = now - timedelta(hours=48)
    purchases_to_release_standard = Purchase.objects.filter(
        status='paid',
        paid_at__lte=standard_cutoff,
        seller__is_verified=False,
        is_escrow_released=False
    )
    
    # Process both
    for purchase in (list(purchases_to_release_verified) + list(purchases_to_release_standard)):
        with transaction.atomic():
            wallet = DJWallet.objects.select_for_update().get(dj=purchase.seller)
            amount = purchase.dj_revenue
            
            if wallet.escrow_amount >= amount:
                wallet.escrow_amount -= amount
                wallet.available_for_payout += amount
                wallet.save()
                
                # Update purchase status
                purchase.is_escrow_released = True
                purchase.save(update_fields=['is_escrow_released'])
                
                # Log the release
                LedgerEntry.objects.create(
                    wallet=wallet,
                    amount=amount,
                    entry_type='credit',
                    description=f"Escrow release for Purchase #{purchase.id}",
                    metadata={'purchase_id': purchase.id, 'action': 'escrow_release'}
                )
                
                records_processed += 1
                total_released += amount

    return records_processed, total_released

def place_earnings_hold(dj_id, hold_type, amount=None, reason='', admin_id=None, notify_dj=True):
    """Missing Item 05: Place an earnings hold on a DJ."""
    from apps.commerce.models import DJWallet, EarningsHold, AdminAuditLog
    wallet = DJWallet.objects.select_for_update().get(dj_id=dj_id)
    hold_amount = amount or wallet.pending_earnings

    if hold_amount > wallet.pending_earnings:
        raise ValueError("Hold amount exceeds pending earnings")

    with transaction.atomic():
        wallet.pending_earnings -= hold_amount
        wallet.escrow_amount += hold_amount
        wallet.save()

        EarningsHold.objects.create(
            dj_id=dj_id,
            amount=hold_amount,
            hold_type=hold_type,
            reason=reason,
            placed_by_id=admin_id,
            status='active'
        )

        AdminAuditLog.objects.create(
            admin_id=admin_id,
            action='place_earnings_hold',
            target_dj_id=dj_id,
            details={'amount': int(hold_amount), 'type': hold_type, 'reason': reason}
        )

    if notify_dj:
        try:
            from apps.admin_panel.email_utils import send_email
            dj_email = wallet.dj.profile.user.email
            send_email(
                to_email=dj_email,
                subject="MixMint Earnings Hold Notice",
                html_content=f"<p>A hold of ₹{hold_amount} has been placed on your earnings for {hold_type.replace('_', ' ')}. Please contact support for more details.</p>"
            )
        except Exception:
            pass

def release_earnings_hold(hold_id, admin_id, outcome='released'):
    """Missing Item 05: Release or forfeit an earnings hold."""
    from apps.commerce.models import EarningsHold, DJWallet, AdminAuditLog
    hold = EarningsHold.objects.select_for_update().get(id=hold_id, status='active')
    wallet = DJWallet.objects.select_for_update().get(dj_id=hold.dj_id)

    with transaction.atomic():
        wallet.escrow_amount -= hold.amount
        
        if outcome == 'released':
            wallet.pending_earnings += hold.amount
            wallet.save()
            try:
                from apps.admin_panel.email_utils import send_email
                dj_email = wallet.dj.profile.user.email
                send_email(
                    to_email=dj_email,
                    subject="MixMint Earnings Hold Released",
                    html_content=f"<p>A hold of ₹{hold.amount} on your earnings has been released.</p>"
                )
            except Exception:
                pass
        else: # forfeited
            wallet.save()
        
        hold.status = outcome
        hold.resolved_by_id = admin_id
        hold.resolved_at = timezone.now()
        hold.save()

        AdminAuditLog.objects.create(
            admin_id=admin_id,
            action=f'resolve_earnings_hold_{outcome}',
            target_dj_id=hold.dj_id,
            details={'hold_id': str(hold.id), 'amount': int(hold.amount)}
        )
