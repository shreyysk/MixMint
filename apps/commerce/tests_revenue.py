from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import DJProfile, User
from apps.commerce.models import DJWallet, Invoice, LedgerEntry, Purchase
from apps.commerce.services import MonetizationService
from apps.tracks.models import Track, TrackCollaborator


class RevenueEngineTest(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(email="test@example.com", password="password")
        self.dj_user = User.objects.create_user(email="dj@example.com", password="password")
        self.dj_profile = self.dj_user.profile
        self.dj_profile.role = "dj"
        self.dj_profile.save(update_fields=["role"])
        self.dj = DJProfile.objects.create(
            profile=self.dj_profile, dj_name="Test DJ", slug="test-dj", status="approved"
        )
        self.track = Track.objects.create(
            dj=self.dj,
            title="Test Track",
            price=Decimal("100.00"),
            file_key="tracks/t.wav",
            preview_type="youtube",
            youtube_url="https://youtube.com/watch?v=abcdefghijk",
        )

    def _paid_purchase(self, price="100.00", fee="0.00"):
        return Purchase.objects.create(
            user=self.buyer.profile,
            content_type="track",
            content_id=self.track.id,
            seller=self.dj,
            original_price=self.track.price,
            price_paid=Decimal(price),
            platform_fee=Decimal(fee),
            status="paid",
            paid_at=timezone.now(),
        )

    def test_standard_commission(self):
        split = MonetizationService.calculate_revenue_split(self.dj, Decimal("100.00"))
        self.assertEqual(split["platform_amount"], Decimal("15.00"))
        self.assertEqual(split["dj_amount"], Decimal("85.00"))

    def test_pro_dj_commission(self):
        self.dj_profile.is_pro_dj = True
        self.dj_profile.save(update_fields=["is_pro_dj"])
        split = MonetizationService.calculate_revenue_split(self.dj, Decimal("100.00"))
        self.assertEqual(split["platform_amount"], Decimal("8.00"))
        self.assertEqual(split["dj_amount"], Decimal("92.00"))

    def test_buyer_fee_is_not_split_with_dj(self):
        purchase = self._paid_purchase(price="105.00", fee="5.00")
        MonetizationService.complete_purchase(purchase)
        purchase.refresh_from_db()
        self.assertEqual(purchase.dj_revenue, Decimal("85.00"))
        wallet = DJWallet.objects.get(dj=self.dj)
        self.assertEqual(wallet.escrow_amount, Decimal("85.00"))
        self.assertEqual(wallet.available_for_payout, Decimal("0.00"))

    def test_complete_purchase_is_idempotent(self):
        purchase = self._paid_purchase()
        MonetizationService.complete_purchase(purchase)
        MonetizationService.complete_purchase(purchase)
        self.assertEqual(Invoice.objects.filter(purchase=purchase).count(), 1)
        self.assertEqual(DJWallet.objects.get(dj=self.dj).total_earnings, Decimal("85.00"))

    def test_collaborator_split(self):
        collab_user = User.objects.create_user(email="collab@example.com", password="password")
        collab_dj = DJProfile.objects.create(
            profile=collab_user.profile, dj_name="Collab DJ", slug="collab-dj", status="approved"
        )
        TrackCollaborator.objects.create(track=self.track, dj=collab_dj, revenue_percentage=Decimal("50.00"))

        MonetizationService.complete_purchase(self._paid_purchase())
        self.assertEqual(DJWallet.objects.get(dj=self.dj).total_earnings, Decimal("42.50"))
        self.assertEqual(DJWallet.objects.get(dj=collab_dj).total_earnings, Decimal("42.50"))

    def test_refund_reverses_every_credit(self):
        purchase = self._paid_purchase()
        MonetizationService.complete_purchase(purchase)
        MonetizationService.reverse_purchase(purchase)
        wallet = DJWallet.objects.get(dj=self.dj)
        self.assertEqual(wallet.total_earnings, Decimal("0.00"))
        self.assertEqual(wallet.escrow_amount, Decimal("0.00"))
        self.assertEqual(LedgerEntry.objects.filter(entry_type="debit").count(), 1)

    def test_escrow_release_after_hold(self):
        from datetime import timedelta

        from apps.commerce.escrow_utils import release_escrow_funds

        purchase = self._paid_purchase()
        MonetizationService.complete_purchase(purchase)
        self.assertEqual(release_escrow_funds()[0], 0)  # still inside the 48h hold
        Purchase.objects.filter(pk=purchase.pk).update(paid_at=timezone.now() - timedelta(hours=49))
        self.assertEqual(release_escrow_funds()[0], 1)
        wallet = DJWallet.objects.get(dj=self.dj)
        self.assertEqual(wallet.available_for_payout, Decimal("85.00"))
        self.assertEqual(wallet.escrow_amount, Decimal("0.00"))
        self.assertEqual(release_escrow_funds()[0], 0)  # idempotent
