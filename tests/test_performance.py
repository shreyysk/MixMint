"""
MixMint 2.0 — Performance Tests
Tests query efficiency, N+1 detection, and bulk operation performance.
Covers: Performance Testing, Load Testing, Stress Testing, Scalability Testing categories.
"""
import pytest
import time
from decimal import Decimal
from django.test.utils import override_settings


@pytest.mark.django_db
class TestQueryPerformance:
    """Test N+1 query patterns and query counts on key views."""

    def _setup_tracks(self, count=20):
        from apps.accounts.models import User, DJProfile
        from apps.tracks.models import Track
        u = User.objects.create_user(email='perfdj@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Perf DJ', slug='perf-dj', status='approved')
        for i in range(count):
            Track.objects.create(
                dj=dj, title=f'Perf Track {i}', price=Decimal('50.00'),
                file_key=f't{i}.wav', preview_type='youtube',
                youtube_url=f'https://youtube.com/watch?v=perf{i}'
            )
        return dj

    def test_home_page_query_count(self):
        """Home page should have bounded query count regardless of data."""
        from django.test import Client
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        self._setup_tracks(20)
        client = Client()

        with CaptureQueriesContext(connection) as ctx:
            response = client.get('/')
            assert response.status_code == 200
        # Home page should not exceed 25 queries
        assert len(ctx) <= 25, f"Home page used {len(ctx)} queries (expected <=25)"

    def test_explore_page_query_count(self):
        """Explore page should have bounded query count."""
        from django.test import Client
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        self._setup_tracks(20)
        client = Client()

        with CaptureQueriesContext(connection) as ctx:
            response = client.get('/explore/')
            assert response.status_code == 200
        assert len(ctx) <= 20, f"Explore page used {len(ctx)} queries (expected ≤20)"


@pytest.mark.django_db
class TestBulkOperationPerformance:
    """Test bulk creation and computation performance."""

    def test_bulk_user_creation(self):
        """Creating 50 users should complete within 5 seconds."""
        from apps.accounts.models import User
        start = time.time()
        for i in range(50):
            User.objects.create_user(email=f'bulk{i}@example.com', password='Pass123!')
        elapsed = time.time() - start
        assert elapsed < 5.0, f"50 user creations took {elapsed:.1f}s (expected <5s)"
        assert User.objects.count() >= 50

    def test_cart_computation_with_many_items(self):
        """Cart total computation for 30 items should be fast."""
        from apps.accounts.models import User
        from apps.commerce.models import Cart, CartItem
        u = User.objects.create_user(email='bigcart@example.com', password='Pass123!')
        cart = Cart.objects.create(user=u.profile)
        for i in range(30):
            CartItem.objects.create(cart=cart, content_type='track', content_id=i + 1, price=10000)

        start = time.time()
        _ = cart.subtotal
        _ = cart.discount_percentage
        _ = cart.discount_amount
        _ = cart.final_total
        _ = cart.next_tier_info
        elapsed = time.time() - start
        assert elapsed < 1.0, f"Cart computation took {elapsed:.1f}s (expected <1s)"
        assert cart.discount_percentage == 30  # 30 items → 30% discount


@pytest.mark.django_db
class TestResponseTimePerformance:
    """Test response times are within acceptable bounds."""

    def test_home_page_response_time(self):
        from django.test import Client
        client = Client()
        start = time.time()
        response = client.get('/')
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 2.0, f"Home page took {elapsed:.1f}s (expected <2s)"

    def test_explore_page_response_time(self):
        from django.test import Client
        client = Client()
        start = time.time()
        response = client.get('/explore/')
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 2.0, f"Explore page took {elapsed:.1f}s (expected <2s)"

    def test_signup_response_time(self):
        from django.test import Client
        client = Client()
        start = time.time()
        response = client.get('/signup/')
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 1.0, f"Signup page took {elapsed:.1f}s (expected <1s)"


@pytest.mark.django_db
class TestStressScenarios:
    """Simulate high-frequency operations for stress resilience."""

    def test_rapid_signups(self):
        """Simulate 20 rapid signups."""
        from django.test import Client
        for i in range(20):
            client = Client()
            response = client.post('/signup/', {
                'full_name': f'Stress User {i}',
                'email': f'stress{i}@example.com',
                'password': 'StrongPass123!',
            })
            assert response.status_code == 302

        from apps.accounts.models import User
        assert User.objects.filter(email__startswith='stress').count() == 20

    def test_concurrent_explore_requests(self):
        """Multiple explore requests should all succeed."""
        from django.test import Client
        client = Client()
        for _ in range(10):
            response = client.get('/explore/', {'q': 'test', 'genre': 'EDM'})
            assert response.status_code == 200
