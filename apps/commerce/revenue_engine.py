"""
MixMint Revenue Engine [Spec P2 §5, P3 §1].

Handles:
- Commission calculation (15% standard, 8% Pro DJ)
- Revenue split for collaborative tracks
- DJ wallet crediting
- Invoice + tax record creation
- Ad revenue share allocation
"""

from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.commerce.models import (
    Purchase, DJWallet, LedgerEntry, Invoice, TaxRecord,
)
from apps.tracks.models import Track, TrackCollaborator
from apps.albums.models import AlbumPack
from apps.admin_panel.models import PlatformSettings, PromotionalOffer

# GST rate for digital goods in India
GST_RATE = Decimal('18.00')  # 18%


def calculate_commission_rate(dj_profile):
    """Get commission rate based on DJ plan [Spec P3 §1.5]."""
    settings_obj = PlatformSettings.load()
    active_offer = PromotionalOffer.objects.filter(is_active=True).first()
    
    if active_offer:
        return settings_obj.platform_commission_rate
        
    if dj_profile.profile.is_pro_dj:
        if settings_obj.platform_commission_rate > Decimal('8.00'):
            return Decimal('8.00')
            
    return settings_obj.platform_commission_rate


def calculate_revenue_split(price, dj_profile, content=None, content_type='track', **kwargs):
    """
    Calculate full revenue breakdown for a purchase [Spec P3 §1].

    Returns dict with:
    - commission: platform commission amount
    - dj_earnings: total DJ earnings (before collab split)
    - checkout_fee: buyer service fee
    - gst_amount: GST on platform commission
    - collaborator_splits: list of (dj, amount) if collab track
    """
    settings_obj = PlatformSettings.load()
    checkout_fee = settings_obj.buyer_platform_fee if settings_obj.buyer_platform_fee_enabled else Decimal('0.00')
    commission_rate = calculate_commission_rate(dj_profile)

    commission = (price * commission_rate / Decimal('100')).quantize(Decimal('0.01'))
    dj_earnings = price - commission

    # GST on commission (platform service)
    gst_amount = Decimal('0.00')
    if settings_obj.gst_charging_enabled:
        gst_amount = (commission * GST_RATE / Decimal('100')).quantize(Decimal('0.01'))

    # Collaborator splits [Spec P2 §4]
    collaborator_splits = []
    if content_type == 'track' and content:
        collabs = TrackCollaborator.objects.filter(track=content)
        if collabs.exists():
            for collab in collabs:
                split_amount = (dj_earnings * collab.revenue_percentage / Decimal('100')).quantize(Decimal('0.01'))
                collaborator_splits.append({
                    'dj': collab.dj,
                    'dj_id': collab.dj.id,
                    'percentage': collab.revenue_percentage,
                    'amount': split_amount,
                })

    # Download Insurance [Spec §4.3]
    insurance_fee = Decimal('15.00') if kwargs.get('with_insurance') else Decimal('0.00')

    return {
        'commission': commission,
        'commission_rate': commission_rate,
        'dj_earnings': dj_earnings,
        'checkout_fee': checkout_fee,
        'gst_amount': gst_amount,
        'collaborator_splits': collaborator_splits,
        'insurance_fee': insurance_fee,
        'total_buyer_pays': price + checkout_fee + insurance_fee,
    }


@transaction.atomic
def create_purchase(user_profile, content_id, content_type, payment_id,
                    payment_order_id=None, is_redownload=False, **kwargs):
    """
    Create a Purchase record after payment verification [Spec P2 §5].
    Handles both single purchases and bulk cart-based itemizations.
    """
    from apps.commerce.models import Bundle, BundlePurchase

    # Price override or discount logic
    price_override = kwargs.get('price_override')
    discount_percentage = kwargs.get('discount_applied', Decimal('0.00'))

    # Resolve content
    if content_type == 'track':
        from apps.tracks.models import Track
        content = Track.objects.get(id=content_id, is_active=True, is_deleted=False)
        dj_profile = content.dj
        price = price_override if price_override is not None else content.price
    elif content_type in ('zip', 'album'):
        from apps.albums.models import AlbumPack
        content = AlbumPack.objects.get(id=content_id, is_active=True, is_deleted=False)
        dj_profile = content.dj
        price = price_override if price_override is not None else content.price
        content_type = 'album'
    elif content_type == 'bundle':
        content = Bundle.objects.get(id=content_id, is_active=True, is_deleted=False)
        dj_profile = content.dj
        price = content.price
        
        bundle_purchase = BundlePurchase.objects.create(
            bundle=content,
            user=user_profile,
            gateway_payment_id=payment_id,
            amount_paid=price,
            dj_revenue=Decimal('0.00'),
        )
        
        tracks_in_bundle = content.bundle_tracks.all()
        track_count = tracks_in_bundle.count()
        if track_count > 0:
            avg_price = (price / Decimal(track_count)).quantize(Decimal('0.01'))
            total_dj_rev = Decimal('0.00')
            
            for bt in tracks_in_bundle:
                inner_p = create_purchase(
                    user_profile, bt.track.id, 'track', payment_id,
                    payment_order_id=payment_order_id, price_override=avg_price
                )
                total_dj_rev += inner_p.dj_revenue
            
            bundle_purchase.dj_revenue = total_dj_rev
            bundle_purchase.save()
            
        return bundle_purchase
    else:
        raise ValueError(f'Invalid content_type: {content_type}')

    # Apply bulk discount if applicable (from Cart checkout)
    if discount_percentage > 0:
        price = (price * (Decimal('100.00') - discount_percentage) / Decimal('100.00')).quantize(Decimal('0.01'))

    # Re-download pricing [Spec §4.3]
    original_price = price
    if is_redownload:
        price = (price * Decimal('0.50')).quantize(Decimal('0.01'))

    # Calculate revenue split
    split = calculate_revenue_split(price, dj_profile, content, content_type)

    # Determine buyer role (Phase 3 Feature 2)
    buyer_role = 'fan'
    if hasattr(user_profile, 'dj_profile') and user_profile.dj_profile:
        buyer_role = 'dj'

    # Create Purchase record
    purchase = Purchase.objects.create(
        user=user_profile,
        content_id=content_id,
        content_type=content_type,
        original_price=original_price,
        price_paid=split['total_buyer_pays'],
        checkout_fee=split['checkout_fee'],
        commission=split['commission'],
        dj_revenue=split['dj_earnings'],
        dj_earnings=split['dj_earnings'],
        ad_revenue_allocated=Decimal('0.00'),
        platform_fee=split['commission'] + split['checkout_fee'] + split.get('insurance_fee', Decimal('0.00')),
        payment_id=payment_id,
        payment_order_id=payment_order_id,
        seller=dj_profile,
        buyer_role=buyer_role,
        is_redownload=is_redownload,
        has_download_insurance=kwargs.get('with_insurance', False),
        is_completed=True,  # Legacy field
        status='paid',      # Canonical field
        download_completed=False,  # Not yet downloaded
    )

    # Credit DJ wallet(s)
    credit_dj_wallets(purchase, dj_profile, split)

    # Check if invoice generation is enabled
    from apps.admin_panel.models import SystemSetting
    invoice_setting_obj = SystemSetting.objects.filter(key='invoice_generation_enabled').first()
    invoice_enabled = invoice_setting_obj.value.get('enabled', True) if invoice_setting_obj and isinstance(invoice_setting_obj.value, dict) else True

    invoice = None
    if invoice_enabled:
        # Create Invoice + Tax records if GST is enabled or just plain invoice
        settings_obj = PlatformSettings.load()
        if settings_obj.gst_charging_enabled:
            pass # Keep tax calculations logic
        invoice = create_purchase_invoice(purchase, user_profile, dj_profile, split)

    # Send purchase success email via Resend [Spec: Buyer invoice email]
    try:
        from apps.admin_panel.email_utils import send_email
        from django.conf import settings

        content_title = content.title if hasattr(content, 'title') else f"{content_type.capitalize()} #{content_id}"
        html_lines = [
            f"<p>Hi {user_profile.full_name or user_profile.user.email},</p>",
            f"<p>Thank you for your purchase on <strong>MixMint</strong>.</p>",
            f"<p><strong>Content:</strong> {content_title} by {dj_profile.dj_name}</p>",
            f"<p><strong>Amount Paid:</strong> ₹{purchase.price_paid}</p>",
        ]
        if invoice:
            html_lines.append(f"<p>Your GST invoice number is <strong>{invoice.invoice_number}</strong>.</p>")

        html_lines.append("<p>You can re-download your purchase from your MixMint library, "
                          "subject to our secure download policy.</p>")
        html_lines.append("<p>— MixMint</p>")

        send_email(
            to_email=user_profile.user.email,
            subject="Your MixMint Purchase & GST Invoice",
            html_content="".join(html_lines),
        )
    except Exception:
        # Email issues must not break purchase creation
        pass

    # Invalidate analytics cache [Fix 11]
    from apps.commerce.analytics import invalidate_dj_analytics
    invalidate_dj_analytics(dj_profile.id)
    for split_item in split.get('collaborator_splits', []):
        invalidate_dj_analytics(split_item['dj_id'])

    # [Missing Item 04] High-value transaction check
    try:
        check_high_value_transaction(purchase)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error checking high value transaction {purchase.id}: {e}")

    return purchase


def credit_dj_wallets(purchase, primary_dj, split):
    """
    Credit earnings to DJ wallet(s) [Spec P2 §9].
    For collab tracks, splits earnings among collaborators.
    Handles escrow for deleted DJ profiles [Fix 05].
    """
    if split['collaborator_splits']:
        # Collaborative track — split earnings among collaborators
        for collab_split in split['collaborator_splits']:
            collab_dj = collab_split['dj']
            wallet, _ = DJWallet.objects.get_or_create(dj=collab_dj)
            
            # TDS Logic [Imp 04]
            gross_amount = collab_split['amount']
            tds_amount = Decimal('0.00')
            if collab_dj.location and 'India' in collab_dj.location:
                tds_amount = (gross_amount * Decimal('0.01')).quantize(Decimal('0.01'))
            net_amount = gross_amount - tds_amount

            if collab_dj.is_deleted:
                wallet.escrow_amount += net_amount
                description = f'Collab revenue ({collab_split["percentage"]}%) from purchase #{purchase.id} (ESCROW - DELETED DJ)'
            else:
                wallet.pending_earnings += net_amount
                wallet.available_for_payout += net_amount
                description = f'Collab revenue ({collab_split["percentage"]}%) from purchase #{purchase.id}'
            
            wallet.total_earnings += net_amount
            wallet.save()

            # Ledger entry
            LedgerEntry.objects.create(
                wallet=wallet,
                amount=net_amount,
                entry_type='credit',
                description=description,
                metadata={
                    'purchase_id': purchase.id,
                    'is_escrow': collab_dj.is_deleted,
                    'gross_amount': str(gross_amount),
                    'tds_deducted': str(tds_amount),
                    'split_percentage': str(collab_split['percentage']),
                },
            )
    else:
        # Solo track/album — full earnings to primary DJ
        wallet, _ = DJWallet.objects.get_or_create(dj=primary_dj)
        
        gross_amount = split['dj_earnings']
        tds_amount = Decimal('0.00')
        if primary_dj.location and 'India' in primary_dj.location:
            tds_amount = (gross_amount * Decimal('0.01')).quantize(Decimal('0.01'))
        net_amount = gross_amount - tds_amount

        if primary_dj.is_deleted:
            wallet.escrow_amount = Decimal(str(wallet.escrow_amount)) + net_amount
            description = f'Revenue from purchase #{purchase.id} (ESCROW - DELETED DJ)'
        else:
            wallet.pending_earnings = Decimal(str(wallet.pending_earnings)) + net_amount
            wallet.available_for_payout = Decimal(str(wallet.available_for_payout)) + net_amount
            description = f'Revenue from purchase #{purchase.id}'
            
        wallet.total_earnings = Decimal(str(wallet.total_earnings)) + net_amount
        wallet.save()

        LedgerEntry.objects.create(
            wallet=wallet,
            amount=net_amount,
            entry_type='credit',
            description=description,
            metadata={
                'purchase_id': purchase.id,
                'is_escrow': primary_dj.is_deleted,
                'gross_amount': str(gross_amount),
                'tds_deducted': str(tds_amount),
            }
        )


def create_purchase_invoice(purchase, user_profile, dj_profile, split):
    """
    Generate Invoice + TaxRecord for a purchase [Spec §9].
    """
    # Generate invoice number
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    invoice_number = f'MM-INV-{timestamp}-{purchase.id}'

    invoice = Invoice.objects.create(
        purchase=purchase,
        user=user_profile,
        dj=dj_profile,
        invoice_number=invoice_number,
        subtotal=purchase.original_price,
        tax_amount=split['gst_amount'],
        total_amount=purchase.price_paid,
        currency='INR',
        status='issued',
    )

    settings_obj = PlatformSettings.load()
    if settings_obj.gst_charging_enabled:
        # GST record
        TaxRecord.objects.create(
            invoice=invoice,
            tax_type='GST',
            tax_rate=GST_RATE,
            tax_amount=split['gst_amount'],
            jurisdiction='India',
        )

    return invoice

def check_high_value_transaction(purchase):
    """Missing Item 04: High-Value Transaction Alerts"""
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Sum
    from apps.commerce.models import TransactionAlert, Purchase
    from apps.accounts.models import Profile

    alerts = []
    user_id = purchase.user_id
    amount = purchase.original_price

    HIGH_VALUE_THRESHOLD = 500.00
    HIGH_VALUE_VELOCITY_THRESHOLD = 300.00

    # Alert 1: Single high-value transaction
    if amount >= HIGH_VALUE_THRESHOLD:
        alerts.append({
            'type': 'high_value_single',
            'message': f'Single purchase of ₹{amount} by user {user_id}',
            'severity': 'HIGH'
        })

    # Alert 2: Velocity — 3+ purchases in 1 hour
    recent_purchases = Purchase.objects.filter(
        user_id=user_id,
        created_at__gte=timezone.now() - timedelta(hours=1),
        status__in=['active', 'pending']
    )
    recent_count = recent_purchases.count()
    if recent_count >= 3:
        recent_total = recent_purchases.aggregate(total=Sum('original_price'))['total'] or 0
        if recent_total >= HIGH_VALUE_VELOCITY_THRESHOLD:
            alerts.append({
                'type': 'high_velocity',
                'message': f'{recent_count} purchases totalling ₹{recent_total} in 1hr',
                'severity': 'HIGH'
            })

    # Alert 3: New account buying high value
    profile = Profile.objects.get(id=user_id)
    account_age_hours = (timezone.now() - profile.created_at).total_seconds() / 3600
    if account_age_hours < 24 and amount >= 200.00:
        alerts.append({
            'type': 'new_account_high_value',
            'message': f'New account (<24h) purchase of ₹{amount}',
            'severity': 'MEDIUM'
        })

    for alert in alerts:
        TransactionAlert.objects.create(
            purchase_id=purchase.id,
            user_id=user_id,
            alert_type=alert['type'],
            message=alert['message'],
            severity=alert['severity']
        )
        if alert['severity'] == 'HIGH':
            try:
                from apps.admin_panel.email_utils import send_email
                from django.conf import settings
                admin_email = getattr(settings, 'ADMIN_ALERT_EMAIL', 'admin@mixmint.site')
                send_email(
                    to_email=admin_email,
                    subject=f"⚠️ MixMint Transaction Alert — {alert['type']}",
                    html_content=f"<p>High-value transaction detected.</p><p>Alert type: {alert['type']}<br>Severity: {alert['severity']}<br>Message: {alert['message']}</p><p>Purchase ID: {purchase.id}<br>User ID: {purchase.user_id}<br>Amount: ₹{amount}<br>Content: {purchase.content_id}<br>Time: {timezone.now().isoformat()}</p>"
                )
            except Exception:
                pass
