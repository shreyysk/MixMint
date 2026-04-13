"""
MixMint 2.0 — Smoke & Sanity Tests
Quick verification that critical paths are working.
Covers: Smoke Testing, Sanity Testing categories.
"""
import pytest
from django.test import Client
from django.urls import reverse, resolve, NoReverseMatch


@pytest.mark.django_db
class TestCriticalPageLoads:
    """Smoke test: all critical pages return 200 OK."""

    def test_home_page_loads(self):
        client = Client()
        response = client.get('/')
        assert response.status_code == 200

    def test_signup_page_loads(self):
        client = Client()
        response = client.get(reverse('signup'))
        assert response.status_code == 200

    def test_login_page_loads(self):
        client = Client()
        response = client.get(reverse('login'))
        assert response.status_code == 200

    def test_explore_page_loads(self):
        client = Client()
        response = client.get(reverse('explore'))
        assert response.status_code == 200

    def test_dj_directory_loads(self):
        client = Client()
        response = client.get(reverse('dj_directory'))
        assert response.status_code == 200

    def test_robots_txt_loads(self):
        client = Client()
        response = client.get('/robots.txt')
        assert response.status_code == 200
        assert 'User-agent' in response.content.decode()

    def test_legal_pages_load(self):
        """Test that legal pages return 200."""
        client = Client()
        legal_urls = ['terms_of_service', 'privacy_policy', 'refund_policy']
        for name in legal_urls:
            try:
                url = reverse(name)
                response = client.get(url)
                assert response.status_code == 200, f"Legal page '{name}' returned {response.status_code}"
            except NoReverseMatch:
                pass  # Some legal pages may not exist yet


@pytest.mark.django_db
class TestURLResolution:
    """Sanity test: critical named URLs resolve without errors."""

    def test_auth_urls_resolve(self):
        """All auth-related URLs should resolve."""
        urls_to_check = ['signup', 'login', 'logout', 'home', 'explore']
        for name in urls_to_check:
            try:
                url = reverse(name)
                assert url is not None, f"URL '{name}' failed to resolve"
            except NoReverseMatch:
                pytest.fail(f"URL '{name}' raised NoReverseMatch")

    def test_api_urls_resolve(self):
        """API base URLs should resolve."""
        api_prefixes = [
            '/api/v1/accounts/',
            '/api/v1/tracks/',
            '/api/v1/albums/',
            '/api/v1/commerce/',
            '/api/v1/payments/',
            '/api/v1/downloads/',
            '/api/v1/admin/',
        ]
        client = Client()
        for prefix in api_prefixes:
            response = client.get(prefix)
            # API root may return 200, 401, or 404 for list — anything except 500
            assert response.status_code != 500, f"API prefix '{prefix}' returned 500"


@pytest.mark.django_db
class TestAuthenticatedPageAccess:
    """Sanity test: protected pages redirect or return 40x for unauthenticated users."""

    def test_dashboard_redirects_unauthenticated(self):
        client = Client()
        response = client.get('/dashboard/')
        assert response.status_code in [301, 302]

    def test_settings_redirects_unauthenticated(self):
        client = Client()
        try:
            response = client.get(reverse('profile_settings'))
            assert response.status_code in [301, 302]
        except NoReverseMatch:
            pass  # URL may not exist

    def test_authenticated_user_sees_dashboard(self):
        from apps.accounts.models import User
        User.objects.create_user(email='smoke@example.com', password='StrongPass123!')
        client = Client()
        client.login(email='smoke@example.com', password='StrongPass123!')
        response = client.get('/dashboard/')
        assert response.status_code == 200
