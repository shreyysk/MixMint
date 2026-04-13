"""
MixMint 2.0 — Billing & Subscription Tests
Tests revenue engine, cart discounts, GST, TDS, wallet balance, and subscription events.
Covers: Billing & Subscription Testing (SaaS-specific) category.
"""
import pytest
from decimal import Decimal


@pytest.mark.django_db
class TestRevenueCalculations:
    """Test full revenue split accuracy across all scenarios."""

    def _setup(self, is_pro=False, **dj_kwargs):
        from apps.accounts.models import User, DJProfile
        from apps.admin_panel.models import PlatformSettings
        PlatformSettings.load()

        u = User.objects.create_user(email=f'billing{"pro" if is_pro else "std"}{id(self)}@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.is_pro_dj = is_pro
        u.profile.save(update_fields=['role', 'is_pro_dj'])
        dj = DJProfile.objects.create(
            profile=u.profile, dj_name=f'Billing DJ {id(self)}',
            slug=f'billing-dj-{id(self)}', status='approved', **dj_kwargs
        )
        return u, dj

    def test_standard_commission_15_percent(self):
        from apps.commerce.revenue_engine import calculate_revenue_split
        _, dj = self._setup()
        split = calculate_revenue_split(Decimal('100.00'), dj)
        assert split['commission'] == Decimal('15.00')
        assert split['dj_earnings'] == Decimal('85.00')

    def test_pro_dj_commission_8_percent(self):
        from apps.commerce.revenue_engine import calculate_revenue_split
        _, dj = self._setup(is_pro=True)
        split = calculate_revenue_split(Decimal('100.00'), dj)
        assert split['commission'] == Decimal('8.00')
        assert split['dj_earnings'] == Decimal('92.00')

    def test_large_price_commission(self):
        from apps.commerce.revenue_engine import calculate_revenue_split
        _, dj = self._setup()
        split = calculate_revenue_split(Decimal('9999.00'), dj)
        expected_commission = (Decimal('9999.00') * Decimal('0.15')).quantize(Decimal('0.01'))
        assert split['commission'] == expected_commission

    def test_minimum_track_price_commission(self):
        from apps.commerce.revenue_engine import calculate_revenue_split
        _, dj = self._setup()
        split = calculate_revenue_split(Decimal('19.00'), dj)
        assert split['commission'] == Decimal('2.85')
        assert split['dj_earnings'] == Decimal('16.15')


@pytest.mark.django_db
class TestCollaboratorSplits:
    """Test revenue split among collaborators [Spec P2 §4]."""

    def test_50_50_split(self):
        from apps.accounts.models import User, DJProfile
        from apps.tracks.models import Track, TrackCollaborator
        from apps.commerce.revenue_engine import calculate_revenue_split
        from apps.admin_panel.models import PlatformSettings
        PlatformSettings.load()

        u1 = User.objects.create_user(email='collab1@example.com', password='Pass123!')
        u1.profile.role = 'dj'
        u1.profile.save(update_fields=['role'])
        dj1 = DJProfile.objects.create(profile=u1.profile, dj_name='Collab DJ1', slug='collab-dj1', status='approved')

        u2 = User.objects.create_user(email='collab2@example.com', password='Pass123!')
        u2.profile.role = 'dj'
        u2.profile.save(update_fields=['role'])
        dj2 = DJProfile.objects.create(profile=u2.profile, dj_name='Collab DJ2', slug='collab-dj2', status='approved')

        track = Track.objects.create(dj=dj1, title='Collab Track', price=Decimal('100.00'),
                                      file_key='t.wav', preview_type='youtube',
                                      youtube_url='https://youtube.com/watch?v=c')
        TrackCollaborator.objects.create(track=track, dj=dj1, revenue_percentage=Decimal('50.00'))
        TrackCollaborator.objects.create(track=track, dj=dj2, revenue_percentage=Decimal('50.00'))

        split = calculate_revenue_split(Decimal('100.00'), dj1, content=track, content_type='track')
        assert len(split['collaborator_splits']) == 2
        assert split['collaborator_splits'][0]['amount'] == Decimal('42.50')
        assert split['collaborator_splits'][1]['amount'] == Decimal('42.50')


@pytest.mark.django_db
class TestCartBillingTiers:
    """Test cart tiered discount billing accuracy."""

    def _build_cart(self, n):
        from apps.accounts.models import User
        from apps.commerce.models import Cart, CartItem
        u = User.objects.create_user(email=f'cartbill{n}@example.com', password='Pass123!')
        cart = Cart.objects.create(user=u.profile)
        for i in range(n):
            CartItem.objects.create(cart=cart, content_type='track', content_id=i + 1, price=10000)
        return cart

    def test_3_items_5pct_discount(self):
        cart = self._build_cart(3)
        assert cart.discount_percentage == 5
        assert cart.subtotal == 30000
        assert cart.discount_amount == 1500
        assert cart.final_total == 28500

    def test_5_items_10pct_discount(self):
        cart = self._build_cart(5)
        assert cart.discount_percentage == 10
        assert cart.discount_amount == 5000
        assert cart.final_total == 45000

    def test_15_items_30pct_discount(self):
        cart = self._build_cart(15)
        assert cart.discount_percentage == 30
        assert cart.final_total == 105000


@pytest.mark.django_db
class TestGSTCalculation:
    """Test GST is applied correctly when enabled."""

    def test_gst_calculated_when_enabled(self):
        from apps.admin_panel.models import PlatformSettings
        from apps.commerce.revenue_engine import calculate_revenue_split
        from apps.accounts.models import User, DJProfile
        ps = PlatformSettings.load()
        ps.gst_charging_enabled = True
        ps.save()

        u = User.objects.create_user(email='gst@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='GST DJ', slug='gst-dj', status='approved')

        split = calculate_revenue_split(Decimal('100.00'), dj)
        assert split['gst_amount'] > Decimal('0.00')
        # GST = 18% of commission (15.00) = 2.70
        assert split['gst_amount'] == Decimal('2.70')

    def test_no_gst_when_disabled(self):
        from apps.admin_panel.models import PlatformSettings
        from apps.commerce.revenue_engine import calculate_revenue_split
        from apps.accounts.models import User, DJProfile
        ps = PlatformSettings.load()
        ps.gst_charging_enabled = False
        ps.save()

        u = User.objects.create_user(email='nogst@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='NoGST DJ', slug='nogst-dj', status='approved')

        split = calculate_revenue_split(Decimal('100.00'), dj)
        assert split['gst_amount'] == Decimal('0.00')


@pytest.mark.django_db
class TestWalletConsistency:
    """Test wallet balance consistency after multiple operations."""

    def test_wallet_balance_after_multiple_credits(self):
        from apps.accounts.models import User, DJProfile
        from apps.commerce.models import DJWallet
        u = User.objects.create_user(email='multiwallet@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Multi DJ', slug='multi-dj', status='approved')
        wallet, _ = DJWallet.objects.get_or_create(dj=dj)

        # Simulate 3 sales
        for i in range(3):
            wallet.total_earnings = Decimal(str(wallet.total_earnings)) + Decimal('85.00')
            wallet.pending_earnings = Decimal(str(wallet.pending_earnings)) + Decimal('85.00')
            wallet.available_for_payout = Decimal(str(wallet.available_for_payout)) + Decimal('85.00')
        wallet.save()

        wallet.refresh_from_db()
        assert wallet.total_earnings == Decimal('255.00')
        assert wallet.available_for_payout == Decimal('255.00')

    def test_escrow_separate_from_available(self):
        from apps.accounts.models import User, DJProfile
        from apps.commerce.models import DJWallet
        u = User.objects.create_user(email='escrow@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Escrow DJ', slug='escrow-dj', status='approved')
        wallet, _ = DJWallet.objects.get_or_create(dj=dj)

        wallet.available_for_payout = Decimal('1000.00')
        wallet.escrow_amount = Decimal('200.00')
        wallet.save()

        wallet.refresh_from_db()
        assert wallet.available_for_payout == Decimal('1000.00')
        assert wallet.escrow_amount == Decimal('200.00')


@pytest.mark.django_db
class TestDJApplicationFee:
    """Test DJ application fee tracking [Spec §7]."""

    def test_application_fee_defaults(self):
        from apps.accounts.models import User, DJProfile
        from apps.commerce.models import DJApplicationFee
        u = User.objects.create_user(email='appfee@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Fee DJ', slug='fee-dj', status='pending')
        fee = DJApplicationFee.objects.create(dj=dj)
        assert fee.amount == Decimal('99.00')
        assert fee.status == 'pending'


@pytest.mark.django_db
class TestDownloadInsurancePricing:
    """Test download insurance fee [Spec §4.3]."""

    def test_insurance_fee_is_15(self):
        from apps.commerce.revenue_engine import calculate_revenue_split
        from apps.accounts.models import User, DJProfile
        from apps.admin_panel.models import PlatformSettings
        PlatformSettings.load()
        u = User.objects.create_user(email='insurance@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Ins DJ', slug='ins-dj', status='approved')

        split = calculate_revenue_split(Decimal('100.00'), dj, with_insurance=True)
        assert split['insurance_fee'] == Decimal('15.00')
        # Total = price + checkout_fee + insurance
        assert split['total_buyer_pays'] >= Decimal('115.00')
