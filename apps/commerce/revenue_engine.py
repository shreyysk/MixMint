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


def calculate_revenue_split(price, dj_profile, content=None, content_type='track'):
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

    return {
        'commission': commission,
        'commission_rate': commission_rate,
        'dj_earnings': dj_earnings,
        'checkout_fee': checkout_fee,
        'gst_amount': gst_amount,
        'collaborator_splits': collaborator_splits,
        'total_buyer_pays': price + checkout_fee,
    }


@transaction.atomic
def create_purchase(user_profile, content_id, content_type, payment_id,
                    payment_order_id=None, is_redownload=False):
    """
    Create a Purchase record after payment verification [Spec P2 §5].

    This is the master function called after Razorpay payment confirmation.
    Handles commission, splits, wallet crediting, and invoice generation.
    """
    # Resolve content
    if content_type == 'track':
        content = Track.objects.get(id=content_id, is_active=True, is_deleted=False)
        dj_profile = content.dj
        price = content.price
    elif content_type in ('zip', 'album'):
        content = AlbumPack.objects.get(id=content_id, is_active=True, is_deleted=False)
        dj_profile = content.dj
        price = content.price
        content_type = 'album'  # Normalize
    else:
        raise ValueError(f'Invalid content_type: {content_type}')

    # Re-download pricing [Spec §4.3]
    original_price = price
    if is_redownload:
        price = (price * Decimal('0.50')).quantize(Decimal('0.01'))

    # Calculate revenue split
    split = calculate_revenue_split(price, dj_profile, content, content_type)

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
        platform_fee=split['commission'] + split['checkout_fee'],
        payment_id=payment_id,
        payment_order_id=payment_order_id,
        seller=dj_profile,
        is_redownload=is_redownload,
        is_completed=True,  # Payment verified
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

    return purchase


def credit_dj_wallets(purchase, primary_dj, split):
    """
    Credit earnings to DJ wallet(s) [Spec P2 §9].
    For collab tracks, splits earnings among collaborators.
    """
    if split['collaborator_splits']:
        # Collaborative track — split earnings among collaborators
        for collab_split in split['collaborator_splits']:
            wallet, _ = DJWallet.objects.get_or_create(dj=collab_split['dj'])
            wallet.pending_earnings += collab_split['amount']
            wallet.total_earnings += collab_split['amount']
            wallet.available_for_payout += collab_split['amount']
            wallet.save()

            # Ledger entry for audit
            LedgerEntry.objects.create(
                wallet=wallet,
                amount=collab_split['amount'],
                entry_type='credit',
                description=f'Collab revenue ({collab_split["percentage"]}%) from purchase #{purchase.id}',
                metadata={
                    'purchase_id': purchase.id,
                    'content_type': purchase.content_type,
                    'content_id': purchase.content_id,
                    'split_percentage': str(collab_split['percentage']),
                },
            )
    else:
        # Solo track/album — full earnings to primary DJ
        wallet, _ = DJWallet.objects.get_or_create(dj=primary_dj)
        wallet.pending_earnings += split['dj_earnings']
        wallet.total_earnings += split['dj_earnings']
        wallet.available_for_payout += split['dj_earnings']
        wallet.save()

        LedgerEntry.objects.create(
            wallet=wallet,
            amount=split['dj_earnings'],
            entry_type='credit',
            description=f'Revenue from purchase #{purchase.id}',
            metadata={
                'purchase_id': purchase.id,
                'content_type': purchase.content_type,
                'content_id': purchase.content_id,
            },
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
