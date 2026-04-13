"""
MixMint 2.0 — Database Tests
Tests schema constraints, model integrity, cascade behavior, and ORM correctness.
Covers: Database Testing category.
"""
import pytest
from decimal import Decimal
from django.db import IntegrityError
from django.core.exceptions import ValidationError


@pytest.mark.django_db
class TestUniqueConstraints:
    """Test unique and unique_together constraints."""

    def test_user_email_unique(self):
        from apps.accounts.models import User
        User.objects.create_user(email='uniq@example.com', password='Pass123!')
        with pytest.raises(IntegrityError):
            User.objects.create_user(email='uniq@example.com', password='Pass123!')

    def test_djprofile_slug_unique(self):
        from apps.accounts.models import User, DJProfile
        u1 = User.objects.create_user(email='slug1@example.com', password='Pass123!')
        u1.profile.role = 'dj'
        u1.profile.save(update_fields=['role'])
        DJProfile.objects.create(profile=u1.profile, dj_name='Slug Test', slug='unique-slug', status='approved')

        u2 = User.objects.create_user(email='slug2@example.com', password='Pass123!')
        u2.profile.role = 'dj'
        u2.profile.save(update_fields=['role'])
        with pytest.raises(IntegrityError):
            DJProfile.objects.create(profile=u2.profile, dj_name='Slug Test 2', slug='unique-slug', status='approved')

    def test_webhook_log_transaction_id_unique(self):
        from apps.commerce.models import WebhookLog
        WebhookLog.objects.create(
            transaction_id='TX001', gateway='phonepe',
            payload={'test': True}, status='SUCCESS'
        )
        with pytest.raises(IntegrityError):
            WebhookLog.objects.create(
                transaction_id='TX001', gateway='phonepe',
                payload={'test': True}, status='SUCCESS'
            )

    def test_user_device_unique_together(self):
        from apps.accounts.models import User, UserDevice
        u = User.objects.create_user(email='device@example.com', password='Pass123!')
        UserDevice.objects.create(user=u, fingerprint='fp123')
        with pytest.raises(IntegrityError):
            UserDevice.objects.create(user=u, fingerprint='fp123')

    def test_ipblacklist_unique_together(self):
        from apps.accounts.models import IPBlacklist
        IPBlacklist.objects.create(type='ip', value='10.0.0.1', reason='test')
        with pytest.raises(IntegrityError):
            IPBlacklist.objects.create(type='ip', value='10.0.0.1', reason='test2')

    def test_wishlist_unique_together(self):
        from apps.accounts.models import User, DJProfile
        from apps.tracks.models import Track
        from apps.commerce.models import Wishlist
        u = User.objects.create_user(email='wish@example.com', password='Pass123!')
        dj_u = User.objects.create_user(email='wishdj@example.com', password='Pass123!')
        dj_u.profile.role = 'dj'
        dj_u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=dj_u.profile, dj_name='Wish DJ', slug='wish-dj', status='approved')
        t = Track.objects.create(dj=dj, title='Wish Track', price=Decimal('50.00'), file_key='t.wav',
                                  preview_type='youtube', youtube_url='https://youtube.com/watch?v=w')
        Wishlist.objects.create(user=u.profile, track=t)
        with pytest.raises(IntegrityError):
            Wishlist.objects.create(user=u.profile, track=t)


@pytest.mark.django_db
class TestCascadeDeletes:
    """Test CASCADE and SET_NULL on foreign key relationships."""

    def test_user_deletion_cascades_to_profile(self):
        from apps.accounts.models import User, Profile
        u = User.objects.create_user(email='cascade@example.com', password='Pass123!')
        profile_pk = u.profile.pk
        u.delete()
        assert not Profile.objects.filter(pk=profile_pk).exists()

    def test_dj_deletion_cascades_tracks(self):
        from apps.accounts.models import User, DJProfile
        from apps.tracks.models import Track
        u = User.objects.create_user(email='cascadedj@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Del DJ', slug='del-dj', status='approved')
        Track.objects.create(dj=dj, title='Del Track', price=Decimal('29.00'), file_key='t.wav',
                              preview_type='youtube', youtube_url='https://youtube.com/watch?v=d')
        dj_id = dj.id
        dj.delete()
        assert Track.objects.filter(dj_id=dj_id).count() == 0

    def test_purchase_deletion_sets_invoice_null(self):
        """Invoice.purchase is SET_NULL, so invoice survives purchase deletion."""
        from apps.accounts.models import User, DJProfile
        from apps.tracks.models import Track
        from apps.commerce.models import Purchase, Invoice
        buyer = User.objects.create_user(email='invbuyer@example.com', password='Pass123!')
        dj_u = User.objects.create_user(email='invdj@example.com', password='Pass123!')
        dj_u.profile.role = 'dj'
        dj_u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=dj_u.profile, dj_name='Inv DJ', slug='inv-dj', status='approved')
        t = Track.objects.create(dj=dj, title='Inv Track', price=Decimal('100.00'), file_key='t.wav',
                                  preview_type='youtube', youtube_url='https://youtube.com/watch?v=i')
        p = Purchase.objects.create(user=buyer.profile, content_id=t.id, content_type='track',
                                     original_price=Decimal('100.00'), price_paid=Decimal('105.00'),
                                     seller=dj, status='paid')
        inv = Invoice.objects.create(purchase=p, user=buyer.profile, dj=dj,
                                      invoice_number='INV-001', subtotal=Decimal('100.00'),
                                      total_amount=Decimal('105.00'))
        p.delete()
        inv.refresh_from_db()
        assert inv.purchase is None  # SET_NULL


@pytest.mark.django_db
class TestJSONFieldDefaults:
    """Test JSONField defaults are properly applied."""

    def test_djprofile_social_links_default_empty_dict(self):
        from apps.accounts.models import User, DJProfile
        u = User.objects.create_user(email='json@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='JSON DJ', slug='json-dj', status='approved')
        assert dj.social_links == {}

    def test_djprofile_genres_default_empty_list(self):
        from apps.accounts.models import User, DJProfile
        u = User.objects.create_user(email='genres@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Genres DJ', slug='genres-dj', status='approved')
        assert dj.genres == []


@pytest.mark.django_db
class TestModelStrMethods:
    """Test __str__ methods on all models that define them."""

    def test_djprofile_str(self):
        from apps.accounts.models import User, DJProfile
        u = User.objects.create_user(email='strtest@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='String DJ', slug='string-dj', status='approved')
        assert str(dj) == 'String DJ'

    def test_profile_str_returns_full_name(self):
        from apps.accounts.models import User
        u = User.objects.create_user(email='profstr@example.com', password='Pass123!')
        u.profile.full_name = 'Full Name'
        u.profile.save(update_fields=['full_name'])
        assert str(u.profile) == 'Full Name'

    def test_djwallet_str(self):
        from apps.accounts.models import User, DJProfile
        from apps.commerce.models import DJWallet
        u = User.objects.create_user(email='walletstr@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Wallet DJ', slug='walletstr-dj', status='approved')
        wallet, _ = DJWallet.objects.get_or_create(dj=dj)
        assert "Wallet DJ" in str(wallet)

    def test_platform_settings_str(self):
        from apps.admin_panel.models import PlatformSettings
        ps = PlatformSettings.load()
        assert 'Platform Settings' in str(ps)
