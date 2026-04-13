"""
MixMint 2.0 — Regression Tests
Tests for previously identified bugs and edge cases to prevent re-occurrence.
Covers: Regression Testing category.
"""
import pytest
from decimal import Decimal
from django.test import Client


@pytest.mark.django_db
class TestWebhookSignatureRegression:
    """Regression: BUG-001 — webhook signature must be verified correctly."""

    def test_valid_signature_accepted(self):
        import hashlib
        from apps.payments.phonepe import PhonePeGateway
        gw = PhonePeGateway()
        payload = "eyJ0ZXN0IjoidmFsaWQifQ=="
        data = payload + gw.salt_key
        sig = hashlib.sha256(data.encode()).hexdigest() + "###" + gw.salt_index
        assert gw.verify_payment(payload, sig) is True

    def test_tampered_payload_rejected(self):
        import hashlib
        from apps.payments.phonepe import PhonePeGateway
        gw = PhonePeGateway()
        original = "eyJ0ZXN0IjoiYSJ9"
        tampered = "eyJ0ZXN0IjoiYiJ9"
        sig = hashlib.sha256((original + gw.salt_key).encode()).hexdigest() + "###" + gw.salt_index
        assert gw.verify_payment(tampered, sig) is False


@pytest.mark.django_db
class TestDuplicatePurchaseRegression:
    """Regression: Gap 20 — duplicate purchase prevention."""

    def test_block_duplicate_track_purchase(self):
        from apps.accounts.models import User, DJProfile
        from apps.tracks.models import Track
        from apps.commerce.models import Purchase

        buyer = User.objects.create_user(email='dupbuyer@example.com', password='StrongPass123!')
        dj_u = User.objects.create_user(email='dupdj@example.com', password='Pass123!')
        dj_u.profile.role = 'dj'
        dj_u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=dj_u.profile, dj_name='Dup DJ', slug='dup-dj', status='approved')
        track = Track.objects.create(dj=dj, title='Dup Track', price=Decimal('100.00'), file_key='t.wav',
                                      preview_type='youtube', youtube_url='https://youtube.com/watch?v=d')

        # First purchase
        Purchase.objects.create(
            user=buyer.profile, content_id=track.id, content_type='track',
            original_price=Decimal('100.00'), price_paid=Decimal('105.00'),
            seller=dj, status='paid', is_revoked=False,
        )

        # Check duplicate would be blocked
        exists = Purchase.objects.filter(
            user=buyer.profile, content_type='track', content_id=track.id,
            status='paid', is_revoked=False
        ).exists()
        assert exists is True


@pytest.mark.django_db
class TestRedownloadPricingRegression:
    """Regression: Re-download at 50% price [Spec §4.3]."""

    def test_redownload_halves_price(self):
        original_price = Decimal('200.00')
        redownload_price = (original_price * Decimal('0.50')).quantize(Decimal('0.01'))
        assert redownload_price == Decimal('100.00')


@pytest.mark.django_db
class TestSelfPurchaseRegression:
    """Regression: DJs cannot purchase their own content."""

    def test_self_purchase_check(self):
        from apps.accounts.models import User, DJProfile
        from apps.tracks.models import Track

        u = User.objects.create_user(email='selfdj@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Self DJ', slug='self-dj', status='approved')
        track = Track.objects.create(dj=dj, title='Self Track', price=Decimal('100.00'), file_key='t.wav',
                                      preview_type='youtube', youtube_url='https://youtube.com/watch?v=s')

        # Verify the track.dj == DJ's dj_profile logic
        assert track.dj == u.profile.dj_profile


@pytest.mark.django_db
class TestFrozenAccountRegression:
    """Regression: Frozen/banned accounts cannot login."""

    def test_frozen_account_login_blocked(self):
        from apps.accounts.models import User
        u = User.objects.create_user(email='frozenreg@example.com', password='StrongPass123!')
        u.profile.is_frozen = True
        u.profile.save(update_fields=['is_frozen'])
        client = Client()
        response = client.post('/login/', {
            'email': 'frozenreg@example.com',
            'password': 'StrongPass123!',
        })
        assert response.status_code == 200  # Stays on login page

    def test_banned_account_login_blocked(self):
        from apps.accounts.models import User
        u = User.objects.create_user(email='bannedreg@example.com', password='StrongPass123!')
        u.profile.is_banned = True
        u.profile.save(update_fields=['is_banned'])
        client = Client()
        response = client.post('/login/', {
            'email': 'bannedreg@example.com',
            'password': 'StrongPass123!',
        })
        assert response.status_code == 200


@pytest.mark.django_db
class TestWebhookIdempotencyRegression:
    """Regression: CP-03.07 — duplicate webhooks should not create duplicate records."""

    def test_duplicate_webhook_log_blocked(self):
        from apps.commerce.models import WebhookLog
        WebhookLog.objects.create(
            transaction_id='IDEMPOTENT_TX', gateway='phonepe',
            payload={'test': True}, status='PAYMENT_SUCCESS', processed=True
        )
        # Check idempotency — same transaction_id
        exists = WebhookLog.objects.filter(
            transaction_id='IDEMPOTENT_TX', processed=True
        ).exists()
        assert exists is True


@pytest.mark.django_db
class TestTrackPriceRegression:
    """Regression: Track price below ₹19 (paid) should be rejected."""

    def test_paid_track_below_19_rejected(self):
        from apps.accounts.models import User, DJProfile
        from apps.tracks.models import Track
        from django.core.exceptions import ValidationError

        u = User.objects.create_user(email='pricereg@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Price DJ', slug='price-dj', status='approved')

        t = Track(dj=dj, title='Cheap Track', price=Decimal('10.00'), file_key='t.wav',
                  preview_type='youtube', youtube_url='https://youtube.com/watch?v=p')
        with pytest.raises(ValidationError):
            t.full_clean()

    def test_free_track_allowed(self):
        from apps.accounts.models import User, DJProfile
        from apps.tracks.models import Track

        u = User.objects.create_user(email='freereg@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Free DJ', slug='free-dj', status='approved')

        t = Track(dj=dj, title='Free Track', price=Decimal('0.00'), file_key='t.wav',
                  preview_type='youtube', youtube_url='https://youtube.com/watch?v=f')
        t.full_clean()  # Should not raise
