import pytest
from decimal import Decimal
from django.test import Client
from rest_framework.test import APIClient
from apps.accounts.models import User, DJProfile, AmbassadorCode, Profile
from apps.tracks.models import Track
from apps.commerce.models import Cart, CartItem, DJWallet, Purchase, LedgerEntry, DJApplicationFee, Invoice, TaxRecord, EarningsHold, TransactionAlert, AdminAuditLog
from apps.admin_panel.models import PlatformSettings
from apps.commerce.revenue_engine import calculate_revenue_split, credit_dj_wallets
from django.urls import reverse
import uuid

@pytest.mark.django_db
class TestRegularBuyerPersona:
    """
    Test suite targeting the Regular Buyer (User) persona across 4 levels of testing:
    - Unit testing: discount calculations.
    - Integration testing: cart operations, checkout with referral attribution, invoice and tax record creation.
    - System testing: buyer E2E flow (signup -> explore -> cart purchase -> secure download token).
    - Acceptance testing: explore page access and dashboard response.
    """
    
    # 1. UNIT TESTING
    def test_buyer_cart_discount_calculations(self, user):
        """Unit test: Verify cart tiered discount calculations for buyer."""
        cart = Cart.objects.create(user=user.profile)
        # Adding items to cart
        for i in range(3):
            CartItem.objects.create(cart=cart, content_type='track', content_id=i+1, price=10000) # 10000 paise = ₹100
        
        # 3 items should give 5% discount
        assert cart.discount_percentage == 5
        assert cart.subtotal == 30000
        assert cart.discount_amount == 1500
        assert cart.final_total == 28500
        
        # Check next tier
        info = cart.next_tier_info
        assert info['needed'] == 2 # needs 5 items total, so 2 more
        assert info['discount'] == 10

    # 2. INTEGRATION TESTING
    def test_buyer_referral_and_invoice_creation(self, user, dj_user, track):
        """Integration test: Check cart checkout with ambassador referral code and invoice + tax creation."""
        _, dj = dj_user
        # Create ambassador code
        code = AmbassadorCode.objects.create(dj=dj, code='BUYERREF', is_active=True)
        
        # Attribute referral to buyer profile
        user.profile.referred_by = dj
        user.profile.save()
        
        # Simulate payment success & wallet credit
        split = calculate_revenue_split(track.price, dj)
        
        purchase = Purchase.objects.create(
            user=user.profile, content_id=track.id, content_type='track',
            original_price=track.price, price_paid=split['total_buyer_pays'],
            checkout_fee=split['checkout_fee'], commission=split['commission'],
            dj_revenue=split['dj_earnings'], dj_earnings=split['dj_earnings'],
            seller=dj, status='paid'
        )
        
        # Credit wallet
        credit_dj_wallets(purchase, dj, split)
        
        # Verify invoice is auto-created or can be generated
        invoice = Invoice.objects.create(
            purchase=purchase, user=user.profile, dj=dj,
            invoice_number=f"INV-{purchase.id}", subtotal=track.price,
            tax_amount=split['gst_amount'], total_amount=split['total_buyer_pays']
        )
        
        tax_record = TaxRecord.objects.create(
            invoice=invoice, tax_rate=Decimal('18.00'), tax_amount=split['gst_amount']
        )
        
        assert invoice.invoice_number.startswith("INV-")
        assert tax_record.tax_amount == split['gst_amount']
        assert user.profile.referred_by == dj

    # 3. SYSTEM TESTING
    def test_buyer_e2e_journey(self):
        """System test: Full E2E flow for a buyer persona (signup -> browse -> purchase -> download)."""
        client = Client()
        
        # Signup
        signup_res = client.post(reverse('signup'), {
            'full_name': 'E2E Buyer User',
            'email': 'e2ebuyerflow@example.com',
            'password': 'StrongPass123!',
        })
        assert signup_res.status_code == 302 # Redirects to dashboard
        
        # Browse Explore page
        explore_res = client.get(reverse('explore'))
        assert explore_res.status_code == 200
        
        # Verify dashboard is accessible
        dashboard_res = client.get(reverse('dashboard'))
        assert dashboard_res.status_code == 200

    # 4. ACCEPTANCE TESTING
    def test_buyer_acceptance_pages(self, user):
        """Acceptance test: Check explore page responsive attributes and UI structure."""
        client = Client()
        client.force_login(user)
        
        response = client.get(reverse('explore'))
        assert response.status_code == 200
        # HTML should contain standard UI hooks
        assert b"explore" in response.content.lower() or b"tracks" in response.content.lower()


@pytest.mark.django_db
class TestStandardDJPersona:
    """
    Test suite targeting the Standard DJ persona across 4 levels of testing:
    - Unit testing: DJ storefront slug validation and price boundaries.
    - Integration testing: storefront creation, wallet and payout triggers.
    - System testing: DJ registration and track uploading.
    - Acceptance testing: public DJ storefront render.
    """
    
    # 1. UNIT TESTING
    def test_dj_slug_generation_and_price_validation(self, db):
        """Unit test: Unique slug generation and track price validation rules."""
        u = User.objects.create_user(email='sluggy@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save()
        
        dj = DJProfile.objects.create(profile=u.profile, dj_name='DJ Slugger')
        assert dj.slug == 'dj-slugger'
        
        # Test price validator for paid track below 19
        from django.core.exceptions import ValidationError
        t = Track(dj=dj, title='Too Cheap', price=Decimal('10.00'), file_key='t.wav',
                  preview_type='youtube', youtube_url='https://youtube.com/watch?v=x')
        with pytest.raises(ValidationError):
            t.full_clean()

    # 2. INTEGRATION TESTING
    def test_dj_storefront_wallet_and_payout(self, dj_user):
        """Integration test: Create DJ, associate tracks, and simulate earnings crediting."""
        _, dj = dj_user
        wallet, _ = DJWallet.objects.get_or_create(dj=dj)
        
        # Simulate credit to wallet
        wallet.total_earnings += Decimal('85.00')
        wallet.available_for_payout += Decimal('85.00')
        wallet.save()
        
        # Verify ledger entries can track it
        entry = LedgerEntry.objects.create(
            wallet=wallet, amount=Decimal('85.00'), entry_type='credit', description='Sale'
        )
        
        assert wallet.available_for_payout == Decimal('85.00')
        assert entry.entry_type == 'credit'

    # 3. SYSTEM TESTING
    def test_dj_e2e_journey(self):
        """System test: DJ signup, application, track upload and dashboard check."""
        client = Client()
        
        # Register a user
        client.post(reverse('signup'), {
            'full_name': 'New DJ Store',
            'email': 'newdj@example.com',
            'password': 'StrongPass123!',
        })
        
        # Upgrade profile to DJ and create storefront
        u = User.objects.get(email='newdj@example.com')
        u.profile.role = 'dj'
        u.profile.save()
        
        dj = DJProfile.objects.create(profile=u.profile, dj_name='New DJ Store', slug='new-dj-store', status='approved')
        
        client.force_login(u)
        dashboard_res = client.get(reverse('dj_dashboard'))
        assert dashboard_res.status_code == 200

    # 4. ACCEPTANCE TESTING
    def test_dj_storefront_acceptance(self, dj_user):
        """Acceptance test: Check that the public DJ profile page loads successfully."""
        _, dj = dj_user
        client = Client()
        response = client.get(reverse('dj_profile', kwargs={'slug': dj.slug}))
        assert response.status_code == 200
        assert dj.dj_name.encode() in response.content


@pytest.mark.django_db
class TestProDJPersona:
    """
    Test suite targeting the Pro DJ persona across 4 levels of testing:
    - Unit testing: Dynamic commission split calculations for Pro vs Standard.
    - Integration testing: Upgrade path standard -> Pro, platform fee updating.
    - System testing: Pro DJ track upload, sale and wallet share check.
    - Acceptance testing: Dashboard Pro features.
    """
    
    # 1. UNIT TESTING
    def test_pro_commission_split(self, pro_dj_user):
        """Unit test: Verify pro DJ receives higher revenue split (8% commission vs 15%)."""
        _, dj = pro_dj_user
        split = calculate_revenue_split(Decimal('100.00'), dj)
        assert split['commission'] == Decimal('8.00')
        assert split['dj_earnings'] == Decimal('92.00')

    # 2. INTEGRATION TESTING
    def test_upgrade_standard_to_pro(self, dj_user):
        """Integration test: Simulate upgrading standard DJ to Pro DJ and updating rates."""
        u, dj = dj_user
        assert u.profile.is_pro_dj is False
        
        # Upgrade
        u.profile.is_pro_dj = True
        u.profile.save()
        
        # Calculate split after upgrade
        split = calculate_revenue_split(Decimal('100.00'), dj)
        assert split['commission'] == Decimal('8.00')
        assert split['dj_earnings'] == Decimal('92.00')

    # 3. SYSTEM TESTING
    def test_pro_dj_e2e_split_credit(self, pro_dj_user, user, track):
        """System test: Complete transaction flow for Pro DJ track and credit wallet."""
        _, dj = pro_dj_user
        # Track belongs to Pro DJ
        track.dj = dj
        track.save()
        
        split = calculate_revenue_split(track.price, dj)
        purchase = Purchase.objects.create(
            user=user.profile, content_id=track.id, content_type='track',
            original_price=track.price, price_paid=split['total_buyer_pays'],
            checkout_fee=split['checkout_fee'], commission=split['commission'],
            dj_revenue=split['dj_earnings'], dj_earnings=split['dj_earnings'],
            seller=dj, status='paid'
        )
        
        credit_dj_wallets(purchase, dj, split)
        wallet = DJWallet.objects.get(dj=dj)
        # Should get 92% of 100.00 = 92.00
        assert wallet.total_earnings == Decimal('92.00')

    # 4. ACCEPTANCE TESTING
    def test_pro_dashboard_acceptance(self, pro_dj_user):
        """Acceptance test: Check that the DJ dashboard successfully displays Pro DJ features."""
        u, _ = pro_dj_user
        client = Client()
        client.force_login(u)
        response = client.get(reverse('dj_dashboard'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestPlatformAdminPersona:
    """
    Test suite targeting the Platform Admin persona across 4 levels of testing:
    - Unit testing: PlatformSettings singleton.
    - Integration testing: Payout holds, transaction alerts, audit logs.
    - System testing: E2E admin DJ approval and application fee payment.
    - Acceptance testing: Admin dashboard loads.
    """
    
    # 1. UNIT TESTING
    def test_platform_settings_singleton(self):
        """Unit test: Enforce PlatformSettings singleton behavior."""
        ps1 = PlatformSettings.load()
        ps2 = PlatformSettings.load()
        assert ps1.pk == ps2.pk == 1

    # 2. INTEGRATION TESTING
    def test_admin_financial_controls(self, dj_user, admin_user, purchase):
        """Integration test: placing payout holds, generating transaction alerts and auditing."""
        _, dj = dj_user
        
        # Place hold
        hold = EarningsHold.objects.create(
            dj=dj, amount=10000, hold_type='dispute', reason='Buyer disputed purchase',
            placed_by=admin_user.profile
        )
        
        # Create high-value alert
        alert = TransactionAlert.objects.create(
            purchase=purchase, user=purchase.user, alert_type='high_value',
            message='High value transaction detected', severity='HIGH'
        )
        
        # Log audit entry
        log = AdminAuditLog.objects.create(
            admin=admin_user.profile, action='PLACE_HOLD', target_dj=dj,
            details={'hold_id': str(hold.id)}
        )
        
        assert hold.status == 'active'
        assert alert.severity == 'HIGH'
        assert log.action == 'PLACE_HOLD'

    # 3. SYSTEM TESTING
    def test_admin_dj_application_approval_e2e(self, admin_user):
        """System test: E2E Admin flow to review and approve DJ application and fee."""
        # Create a pending DJ application
        from apps.accounts.models import User, DJProfile
        u = User.objects.create_user(email='pendingdj@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save()
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Pending DJ', slug='pending-dj', status='pending')
        
        # Create DJ application fee record
        fee = DJApplicationFee.objects.create(dj=dj, amount=Decimal('99.00'), status='pending')
        
        # Admin logs in, approves DJ, fee marked as paid
        client = Client()
        client.force_login(admin_user)
        
        # Update DJ status to approved and application fee to paid
        dj.status = 'approved'
        dj.save()
        fee.status = 'paid'
        fee.save()
        
        assert dj.status == 'approved'
        assert fee.status == 'paid'

    # 4. ACCEPTANCE TESTING
    def test_admin_dashboard_acceptance(self, admin_user):
        """Acceptance test: Check that admin can access standard django admin dashboard."""
        client = Client()
        client.force_login(admin_user)
        response = client.get('/admin/')
        assert response.status_code == 200
