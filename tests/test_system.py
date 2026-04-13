"""
MixMint 2.0 — System / End-to-End Tests
Tests complete user journeys across the full application stack.
Covers: System Testing, End-to-End (E2E) Testing categories.
"""
import pytest
from decimal import Decimal
from django.test import Client


@pytest.mark.django_db
class TestBuyerJourney:
    """E2E: Full buyer journey — signup → explore → purchase flow."""

    def test_buyer_can_signup_and_explore(self):
        client = Client()
        # 1. Signup
        response = client.post('/signup/', {
            'full_name': 'E2E Buyer',
            'email': 'e2ebuyer@example.com',
            'password': 'StrongPass123!',
        })
        assert response.status_code == 302  # Redirect to dashboard

        # 2. Explore tracks
        response = client.get('/explore/')
        assert response.status_code == 200

        # 3. Dashboard
        response = client.get('/dashboard/')
        assert response.status_code == 200

    def test_buyer_can_browse_dj_directory(self):
        client = Client()
        response = client.get('/djs/')
        assert response.status_code == 200

    def test_buyer_search_by_genre(self):
        from apps.accounts.models import User, DJProfile
        from apps.tracks.models import Track
        u = User.objects.create_user(email='searchdj@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Genre DJ', slug='genre-dj', status='approved')
        Track.objects.create(dj=dj, title='Bollywood Beat', price=Decimal('50.00'),
                              file_key='t.wav', preview_type='youtube',
                              youtube_url='https://youtube.com/watch?v=g', genre='Bollywood')

        client = Client()
        response = client.get('/explore/', {'genre': 'Bollywood'})
        assert response.status_code == 200
        assert b'Bollywood Beat' in response.content

    def test_buyer_search_by_query(self):
        from apps.accounts.models import User, DJProfile
        from apps.tracks.models import Track
        u = User.objects.create_user(email='querydj@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Query DJ', slug='query-dj', status='approved')
        Track.objects.create(dj=dj, title='Unique Track Name', price=Decimal('50.00'),
                              file_key='t.wav', preview_type='youtube',
                              youtube_url='https://youtube.com/watch?v=q')

        client = Client()
        response = client.get('/explore/', {'q': 'Unique Track'})
        assert response.status_code == 200
        assert b'Unique Track Name' in response.content


@pytest.mark.django_db
class TestDJJourney:
    """E2E: DJ journey — signup → dashboard → manage."""

    def test_dj_dashboard_access_after_login(self):
        from apps.accounts.models import User, DJProfile
        u = User.objects.create_user(email='djjourney@example.com', password='StrongPass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        DJProfile.objects.create(profile=u.profile, dj_name='Journey DJ', slug='journey-dj', status='approved')

        client = Client()
        client.login(email='djjourney@example.com', password='StrongPass123!')
        response = client.get('/dashboard/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestAdminJourney:
    """E2E: Admin journey — login → dashboard → settings."""

    def test_admin_full_flow(self):
        from apps.accounts.models import User
        from apps.admin_panel.models import PlatformSettings
        PlatformSettings.load()

        admin = User.objects.create_superuser(email='e2eadmin@example.com', password='AdminPass123!')
        admin.profile.role = 'admin'
        admin.profile.save(update_fields=['role'])

        client = Client()
        client.login(email='e2eadmin@example.com', password='AdminPass123!')

        # Dashboard
        response = client.get('/admin/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestExploreFilters:
    """E2E: Explore page filter combinations."""

    def test_price_filter(self):
        from apps.accounts.models import User, DJProfile
        from apps.tracks.models import Track
        u = User.objects.create_user(email='pricefilt@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Price DJ', slug='pricefilt-dj', status='approved')
        Track.objects.create(dj=dj, title='Cheap Track', price=Decimal('19.00'), file_key='t.wav',
                              preview_type='youtube', youtube_url='https://youtube.com/watch?v=p')
        Track.objects.create(dj=dj, title='Expensive Track', price=Decimal('999.00'), file_key='t2.wav',
                              preview_type='youtube', youtube_url='https://youtube.com/watch?v=p2')

        client = Client()
        response = client.get('/explore/', {'price_max': '100'})
        assert response.status_code == 200
        assert b'Cheap Track' in response.content

    def test_sort_by_popular(self):
        client = Client()
        response = client.get('/explore/', {'sort': 'popular'})
        assert response.status_code == 200

    def test_sort_by_price_low(self):
        client = Client()
        response = client.get('/explore/', {'sort': 'price_low'})
        assert response.status_code == 200
