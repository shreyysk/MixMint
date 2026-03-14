from decimal import Decimal
from django.db import transaction
from .models import DJWallet, LedgerEntry, Invoice, TaxRecord
from apps.admin_panel.models import PlatformSettings, PromotionalOffer
import time
import random


class MonetizationService:
    @staticmethod
    def get_commission_rate(dj_profile):
        """
        Returns commission rate based on DJ tier or PlatformSettings.
        If a promotional offer is active, it overrides everything via the global PlatformSettings.
        Otherwise, Pro DJs might get a default of 8%.
        """
        settings = PlatformSettings.load()
        active_offer = PromotionalOffer.objects.filter(is_active=True).first()
        
        # If there's an active offer, we adhere to the global setting strictly:
        if active_offer:
            return settings.platform_commission_rate
            
        # Optional: Custom fallback logic if NO offer is active
        # The spec indicates the global admin rate applies. Let's just use the global rate
        # unless Pro overrides it. We'll stick to the global rate.
        if dj_profile.is_pro_dj:
            # Let's preserve 8% for pro, unless the global rate is even lower (e.g. 5% promo)
            if settings.platform_commission_rate > Decimal('8.00'):
                return Decimal('8.00')
                
        return settings.platform_commission_rate

    @staticmethod
    def calculate_revenue_split(dj_profile, total_amount):
        """
        Calculates split between DJ and Platform.
        Regular: 85% DJ, 15% Platform
        Pro DJ: 92% DJ, 8% Platform
        """
        commission_rate = MonetizationService.get_commission_rate(dj_profile)
        platform_amount = (total_amount * commission_rate) / Decimal('100.00')
        dj_amount = total_amount - platform_amount

        return {
            'dj_amount': dj_amount,
            'platform_amount': platform_amount,
            'commission_rate': commission_rate
        }

    @staticmethod
    def record_revenue(dj_profile, amount, sale_type, reference_id, track=None):
        """
        Updates DJ wallet and records ledger.
        If track has collaborators, splits DJ's share among them [Spec P2 §4].
        """
        with transaction.atomic():
            split = MonetizationService.calculate_revenue_split(dj_profile, amount)
            dj_total = split['dj_amount']

            # Check for collaborators
            collaborators = []
            if track and hasattr(track, 'collaborators'):
                collaborators = list(track.collaborators.all())

            if collaborators:
                # Split DJ amount among collaborators by percentage
                for collab in collaborators:
                    collab_amount = (dj_total * collab.revenue_percentage) / Decimal('100.00')
                    wallet, _ = DJWallet.objects.get_or_create(dj=collab.dj)
                    from django.db.models import F
                    wallet.total_earnings = F('total_earnings') + collab_amount
                    wallet.pending_earnings = F('pending_earnings') + collab_amount
                    wallet.available_for_payout = F('available_for_payout') + collab_amount
                    wallet.save(update_fields=['total_earnings', 'pending_earnings', 'available_for_payout'])

                    LedgerEntry.objects.create(
                        wallet=wallet,
                        amount=collab_amount,
                        entry_type='credit',
                        description=f"Collab revenue from {sale_type} ({reference_id})",
                        metadata={
                            'commission_rate': str(split['commission_rate']),
                            'collab_percentage': str(collab.revenue_percentage),
                            'reference_id': reference_id,
                            'type': sale_type
                        }
                    )
            else:
                # Solo track — all revenue to single DJ
                wallet, _ = DJWallet.objects.get_or_create(dj=dj_profile)
                from django.db.models import F
                wallet.total_earnings = F('total_earnings') + dj_total
                wallet.pending_earnings = F('pending_earnings') + dj_total
                wallet.available_for_payout = F('available_for_payout') + dj_total
                wallet.save(update_fields=['total_earnings', 'pending_earnings', 'available_for_payout'])

                LedgerEntry.objects.create(
                    wallet=wallet,
                    amount=dj_total,
                    entry_type='credit',
                    description=f"Revenue from {sale_type} ({reference_id})",
                    metadata={
                        'commission_rate': str(split['commission_rate']),
                        'platform_amount': str(split['platform_amount']),
                        'reference_id': reference_id,
                        'type': sale_type
                    }
                )

            return split

    @staticmethod
    def generate_invoice(purchase):
        """
        Generates invoice and tax records silently using unified PlatformSettings.
        """
        settings = PlatformSettings.load()
        subtotal = purchase.price_paid
        
        tax_amount = Decimal('0.00')
        tax_rate = Decimal('18.00')
        
        # If GST is enabled, calculate backward (Inclusive Pricing Rule)
        # So subtotal is the total amount (buyer only sees one number)
        # And tax_amount is subtotal - (subtotal / 1.18)
        total_amount = subtotal
        
        if settings.gst_charging_enabled:
            # Formula for inclusive tax: Tax = Total - (Total / (1 + Rate))
            base_price = subtotal / (Decimal('1') + (tax_rate / Decimal('100.00')))
            tax_amount = subtotal - base_price
            subtotal = base_price  # The subtotal on the invoice is the base price

        invoice_number = f"INV-{int(time.time())}-{random.randint(100, 999)}"

        with transaction.atomic():
            invoice = Invoice.objects.create(
                purchase=purchase,
                user=purchase.user,
                dj=purchase.seller,
                invoice_number=invoice_number,
                subtotal=subtotal,
                tax_amount=tax_amount,
                total_amount=total_amount,
                status='issued'
            )

            TaxRecord.objects.create(
                invoice=invoice,
                tax_type='GST',
                tax_rate=tax_rate,
                tax_amount=tax_amount,
                jurisdiction='India'
            )
            return invoice

    @staticmethod
    def complete_purchase(purchase):
        """
        Main entry point for post-payment processing [Spec P2 §4, §5, §6].
        1. Distribute revenue
        2. Generate invoice
        3. Check verification status
        """
        from apps.accounts.utils import check_verification_eligibility
        
        with transaction.atomic():
            # 1. Distribute revenue
            track_obj = None
            if purchase.content_type == 'track':
                from apps.tracks.models import Track
                try:
                    track_obj = Track.objects.get(id=purchase.content_id)
                except Track.DoesNotExist:
                    pass

            MonetizationService.record_revenue(
                dj_profile=purchase.seller,
                amount=purchase.price_paid,
                sale_type=purchase.content_type,
                reference_id=str(purchase.id),
                track=track_obj
            )

            # 2. Generate invoice
            MonetizationService.generate_invoice(purchase)

            # 3. Check verification status for the seller
            if purchase.seller:
                check_verification_eligibility(purchase.seller)
