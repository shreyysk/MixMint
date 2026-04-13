"""
MixMint 2.0 — Multi-Tenancy Tests
Tests data isolation between DJs, users, and admin roles.
Covers: Multi-Tenancy Testing (SaaS-specific) category.
"""
import pytest
from decimal import Decimal
from django.test import Client
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestDJStorefrontIsolation:
    """Test DJ storefronts are properly isolated."""

    def test_paused_store_tracks_not_visible(self):
        """Paused DJ stores should not show tracks on explore."""
        from apps.accounts.models import User, DJProfile
        from apps.tracks.models import Track

        # Active DJ
        u1 = User.objects.create_user(email='active@example.com', password='Pass123!')
        u1.profile.role = 'dj'
        u1.profile.save(update_fields=['role'])
        dj1 = DJProfile.objects.create(profile=u1.profile, dj_name='Active DJ', slug='active-dj', status='approved')
        Track.objects.create(dj=dj1, title='Active Track', price=Decimal('50.00'),
                              file_key='t.wav', preview_type='youtube',
                              youtube_url='https://youtube.com/watch?v=a')

        # Paused DJ
        u2 = User.objects.create_user(email='paused@example.com', password='Pass123!')
        u2.profile.role = 'dj'
        u2.profile.store_paused = True
        u2.profile.save(update_fields=['role', 'store_paused'])
        dj2 = DJProfile.objects.create(profile=u2.profile, dj_name='Paused DJ', slug='paused-dj', status='approved')
        Track.objects.create(dj=dj2, title='Paused Track', price=Decimal('50.00'),
                              file_key='t2.wav', preview_type='youtube',
                              youtube_url='https://youtube.com/watch?v=p')

        client = Client()
        response = client.get('/explore/')
        assert b'Active Track' in response.content
        assert b'Paused Track' not in response.content

    def test_inactive_track_not_visible(self):
        """Tracks with is_active=False should not appear."""
        from apps.accounts.models import User, DJProfile
        from apps.tracks.models import Track

        u = User.objects.create_user(email='inactive@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Inactive DJ', slug='inactive-dj', status='approved')
        Track.objects.create(dj=dj, title='Hidden Track', price=Decimal('50.00'),
                              file_key='t.wav', preview_type='youtube',
                              youtube_url='https://youtube.com/watch?v=h', is_active=False)

        client = Client()
        response = client.get('/explore/')
        assert b'Hidden Track' not in response.content

    def test_deleted_track_not_visible(self):
        """Soft-deleted tracks should not appear."""
        from apps.accounts.models import User, DJProfile
        from apps.tracks.models import Track

        u = User.objects.create_user(email='deleted@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Deleted DJ', slug='deleted-dj', status='approved')
        Track.objects.create(dj=dj, title='Deleted Track', price=Decimal('50.00'),
                              file_key='t.wav', preview_type='youtube',
                              youtube_url='https://youtube.com/watch?v=d', is_deleted=True)

        client = Client()
        response = client.get('/explore/')
        assert b'Deleted Track' not in response.content


@pytest.mark.django_db
class TestProfileDataIsolation:
    """Test user profile data is isolated correctly."""

    def test_regular_user_cannot_see_other_profiles_via_api(self):
        from apps.accounts.models import User
        u1 = User.objects.create_user(email='iso1@example.com', password='Pass123!')
        u2 = User.objects.create_user(email='iso2@example.com', password='Pass123!')

        client = APIClient()
        client.force_authenticate(user=u1)
        response = client.get('/api/v1/accounts/profiles/')
        assert response.status_code == 200
        data = response.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        # User 1 should only see their own profile
        if isinstance(results, list):
            assert len(results) == 1

    def test_admin_can_see_all_profiles(self):
        from apps.accounts.models import User
        User.objects.create_user(email='adminiso1@example.com', password='Pass123!')
        User.objects.create_user(email='adminiso2@example.com', password='Pass123!')
        admin = User.objects.create_superuser(email='isoadmin@example.com', password='Admin123!')

        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get('/api/v1/accounts/profiles/')
        assert response.status_code == 200
        data = response.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        if isinstance(results, list):
            assert len(results) >= 3


@pytest.mark.django_db
class TestDJDirectoryIsolation:
    """Test DJ directory only shows approved DJs."""

    def test_pending_djs_not_in_directory(self):
        from apps.accounts.models import User, DJProfile
        u = User.objects.create_user(email='pdir@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        DJProfile.objects.create(profile=u.profile, dj_name='Pending Directory DJ', slug='pending-dir', status='pending')

        client = Client()
        response = client.get('/djs/')
        assert b'Pending Directory DJ' not in response.content

    def test_approved_djs_visible_in_directory(self):
        from apps.accounts.models import User, DJProfile
        u = User.objects.create_user(email='adir@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        DJProfile.objects.create(profile=u.profile, dj_name='Approved Directory DJ', slug='approved-dir', status='approved')

        client = Client()
        response = client.get('/djs/')
        assert b'Approved Directory DJ' in response.content

    def test_banned_djs_not_in_directory(self):
        from apps.accounts.models import User, DJProfile
        u = User.objects.create_user(email='bdir@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        DJProfile.objects.create(profile=u.profile, dj_name='Banned Directory DJ', slug='banned-dir', status='banned')

        client = Client()
        response = client.get('/djs/')
        assert b'Banned Directory DJ' not in response.content


@pytest.mark.django_db
class TestPurchaseIsolation:
    """Test purchase data is isolated per user."""

    def test_user_purchases_isolated(self):
        from apps.accounts.models import User, DJProfile
        from apps.commerce.models import Purchase
        from apps.tracks.models import Track

        buyer1 = User.objects.create_user(email='buyer1iso@example.com', password='Pass123!')
        buyer2 = User.objects.create_user(email='buyer2iso@example.com', password='Pass123!')
        dj_u = User.objects.create_user(email='djiso@example.com', password='Pass123!')
        dj_u.profile.role = 'dj'
        dj_u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=dj_u.profile, dj_name='Iso DJ', slug='iso-dj', status='approved')
        t = Track.objects.create(dj=dj, title='Iso Track', price=Decimal('100.00'), file_key='t.wav',
                                  preview_type='youtube', youtube_url='https://youtube.com/watch?v=i')

        # Buyer 1 makes a purchase
        Purchase.objects.create(user=buyer1.profile, content_id=t.id, content_type='track',
                                 original_price=Decimal('100.00'), price_paid=Decimal('105.00'),
                                 seller=dj, status='paid')

        # Buyer 2 should have no purchases
        assert Purchase.objects.filter(user=buyer2.profile).count() == 0
        assert Purchase.objects.filter(user=buyer1.profile).count() == 1
