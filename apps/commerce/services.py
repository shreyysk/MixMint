from decimal import Decimal
from django.db import transaction
from .models import DJWallet, LedgerEntry, Invoice, TaxRecord
import time
import random


class MonetizationService:
    @staticmethod
    def get_commission_rate(dj_profile):
        """
        Returns commission rate based on DJ tier.
        Pro DJs get 8% commission, regular DJs get 15% [Spec P3 §1.5].
        """
        if dj_profile.is_pro_dj:
            return Decimal('8.00')
        return Decimal('15.00')

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
                    wallet.total_earnings += collab_amount
                    wallet.pending_earnings += collab_amount
                    wallet.available_for_payout += collab_amount
                    wallet.save()

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
                wallet.total_earnings += dj_total
                wallet.pending_earnings += dj_total
                wallet.available_for_payout += dj_total
                wallet.save()

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
        Generates invoice and tax records with 18% GST.
        """
        subtotal = purchase.price_paid
        tax_rate = Decimal('18.00')
        tax_amount = (subtotal * tax_rate) / Decimal('100.00')
        total_amount = subtotal + tax_amount

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
