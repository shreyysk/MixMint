"""
MixMint 2.0 — Integration Tests
Tests component interactions across multiple modules.
Covers: Integration Testing category.
"""
import pytest
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse


@pytest.mark.django_db
class TestAuthFlowIntegration:
    """Test signup → profile creation → login → dashboard flow."""

    def test_signup_creates_user_and_profile(self):
        client = Client()
        response = client.post(reverse('signup'), {
            'full_name': 'Integration User',
            'email': 'integ@example.com',
            'password': 'StrongPass123!',
        })
        assert response.status_code == 302  # Redirect to dashboard

        from apps.accounts.models import User
        u = User.objects.get(email='integ@example.com')
        assert u.profile.full_name == 'Integration User'
        assert u.profile.role == 'user'

    def test_login_redirects_to_dashboard(self):
        from apps.accounts.models import User
        User.objects.create_user(email='login@example.com', password='StrongPass123!')
        client = Client()
        response = client.post(reverse('login'), {
            'email': 'login@example.com',
            'password': 'StrongPass123!',
        })
        assert response.status_code == 302

    def test_login_records_history(self):
        from apps.accounts.models import User, LoginHistory
        u = User.objects.create_user(email='hist@example.com', password='StrongPass123!')
        client = Client()
        client.post(reverse('login'), {
            'email': 'hist@example.com',
            'password': 'StrongPass123!',
        })
        assert LoginHistory.objects.filter(user=u).count() >= 1

    def test_signup_records_login_history(self):
        from apps.accounts.models import LoginHistory
        client = Client()
        client.post(reverse('signup'), {
            'full_name': 'History User',
            'email': 'history@example.com',
            'password': 'StrongPass123!',
        })
        from apps.accounts.models import User
        u = User.objects.get(email='history@example.com')
        assert LoginHistory.objects.filter(user=u).exists()

    def test_frozen_account_cannot_login(self):
        from apps.accounts.models import User
        u = User.objects.create_user(email='frozen@example.com', password='StrongPass123!')
        u.profile.is_frozen = True
        u.profile.save(update_fields=['is_frozen'])
        client = Client()
        response = client.post(reverse('login'), {
            'email': 'frozen@example.com',
            'password': 'StrongPass123!',
        })
        # Should stay on login page with error
        assert response.status_code == 200

    def test_banned_account_cannot_login(self):
        from apps.accounts.models import User
        u = User.objects.create_user(email='banned@example.com', password='StrongPass123!')
        u.profile.is_banned = True
        u.profile.save(update_fields=['is_banned'])
        client = Client()
        response = client.post(reverse('login'), {
            'email': 'banned@example.com',
            'password': 'StrongPass123!',
        })
        assert response.status_code == 200  # Stay on login page


@pytest.mark.django_db
class TestReferralIntegration:
    """Test referral code tracking across signup flow [Imp 15]."""

    def test_referral_code_tracked_on_signup(self):
        from apps.accounts.models import User, DJProfile, AmbassadorCode
        # Create DJ with ambassador code
        dj_u = User.objects.create_user(email='ambassador@example.com', password='Pass123!')
        dj_u.profile.role = 'dj'
        dj_u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=dj_u.profile, dj_name='Ambassador DJ', slug='ambassador-dj', status='approved')
        code = AmbassadorCode.objects.create(dj=dj, code='TESTREF', is_active=True)

        client = Client()
        # First visit with ?ref=TESTREF
        client.get('/', {'ref': 'TESTREF'})
        # Then signup
        client.post(reverse('signup'), {
            'full_name': 'Referred User',
            'email': 'referred@example.com',
            'password': 'StrongPass123!',
        })

        user = User.objects.get(email='referred@example.com')
        assert user.profile.referred_by == dj
        code.refresh_from_db()
        assert code.referral_count == 1


@pytest.mark.django_db
class TestWalletCreditIntegration:
    """Test purchase → wallet crediting → ledger entry flow."""

    def test_purchase_credits_dj_wallet(self):
        from apps.accounts.models import User, DJProfile
        from apps.tracks.models import Track
        from apps.commerce.models import DJWallet, LedgerEntry
        from apps.commerce.revenue_engine import calculate_revenue_split, credit_dj_wallets
        from apps.commerce.models import Purchase
        from apps.admin_panel.models import PlatformSettings
        PlatformSettings.load()

        # Setup
        buyer = User.objects.create_user(email='walletbuyer@example.com', password='Pass123!')
        dj_u = User.objects.create_user(email='walletdj@example.com', password='Pass123!')
        dj_u.profile.role = 'dj'
        dj_u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=dj_u.profile, dj_name='Wallet DJ', slug='wallet-dj', status='approved')
        track = Track.objects.create(dj=dj, title='Wallet Track', price=Decimal('200.00'),
                                      file_key='t.wav', preview_type='youtube',
                                      youtube_url='https://youtube.com/watch?v=w')

        split = calculate_revenue_split(track.price, dj)

        purchase = Purchase.objects.create(
            user=buyer.profile, content_id=track.id, content_type='track',
            original_price=track.price, price_paid=split['total_buyer_pays'],
            commission=split['commission'], dj_revenue=split['dj_earnings'],
            dj_earnings=split['dj_earnings'], seller=dj, status='paid',
        )

        credit_dj_wallets(purchase, dj, split)

        wallet = DJWallet.objects.get(dj=dj)
        assert wallet.total_earnings > 0
        assert LedgerEntry.objects.filter(wallet=wallet).exists()


@pytest.mark.django_db
class TestWaitlistIntegration:
    """Test waitlist signup flow [Imp 10]."""

    def test_waitlist_signup_success(self):
        import json
        client = Client()
        response = client.post(
            reverse('waitlist_signup'),
            data=json.dumps({'email': 'waitlist@example.com', 'is_dj': True, 'source': 'test'}),
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.json()
        assert 'Success' in data['message'] or 'waitlist' in data['message'].lower()

    def test_duplicate_waitlist_returns_message(self):
        import json
        from apps.accounts.models import Waitlist
        Waitlist.objects.create(email='dup@example.com')
        client = Client()
        response = client.post(
            reverse('waitlist_signup'),
            data=json.dumps({'email': 'dup@example.com'}),
            content_type='application/json',
        )
        assert response.status_code == 200
        assert 'already' in response.json()['message'].lower()
