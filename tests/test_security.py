"""
MixMint 2.0 — Security & Penetration Tests
Tests security boundaries, middleware, auth enforcement, and attack resistance.
Covers: Security Testing, Penetration Testing categories.
"""
import pytest
from django.test import Client, RequestFactory
from django.http import JsonResponse


# ============================================================
# 1. IP SESSION MIDDLEWARE TESTS
# ============================================================

@pytest.mark.django_db
class TestIPSessionMiddleware:
    """Tests IP binding and forced logout on IP change [Spec §13]."""

    def test_ip_bound_on_login(self):
        from apps.accounts.models import User
        User.objects.create_user(email='ipsession@example.com', password='StrongPass123!')
        client = Client(REMOTE_ADDR='10.0.0.1')
        client.post('/login/', {'email': 'ipsession@example.com', 'password': 'StrongPass123!'})
        session = client.session
        assert session.get('bound_ip') == '10.0.0.1'

    def test_ip_change_triggers_logout(self):
        from apps.accounts.models import User
        User.objects.create_user(email='ipchange@example.com', password='StrongPass123!')
        # Login from IP 1
        client = Client(REMOTE_ADDR='10.0.0.1')
        client.post('/login/', {'email': 'ipchange@example.com', 'password': 'StrongPass123!'})

        # Make a request from different IP — middleware should detect change
        from apps.accounts.middleware import IPSessionMiddleware
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/api/v1/tracks/', REMOTE_ADDR='10.0.0.2')
        # Simulate session with bound_ip
        from django.contrib.sessions.backends.db import SessionStore
        request.session = SessionStore()
        request.session['bound_ip'] = '10.0.0.1'

        # Simulate authenticated user
        from apps.accounts.models import User as UserModel
        request.user = UserModel.objects.get(email='ipchange@example.com')

        middleware = IPSessionMiddleware(get_response=lambda r: None)
        response = middleware.process_request(request)
        assert response is not None
        assert response.status_code == 401


# ============================================================
# 2. BLACKLIST MIDDLEWARE TESTS
# ============================================================

@pytest.mark.django_db
class TestBlacklistMiddleware:
    """Tests IP/device/CIDR blacklisting [Missing Item 03]."""

    def test_blocked_ip_returns_403(self):
        from apps.accounts.models import IPBlacklist
        from django.core.cache import cache
        cache.clear()  # Clear cached blacklist

        IPBlacklist.objects.create(type='ip', value='192.168.1.100', reason='Test ban')
        client = Client(REMOTE_ADDR='192.168.1.100')
        response = client.get('/')
        assert response.status_code == 403

    def test_allowed_ip_passes(self):
        from django.core.cache import cache
        cache.clear()
        client = Client(REMOTE_ADDR='10.0.0.50')
        response = client.get('/')
        assert response.status_code != 403

    def test_blocked_device_returns_403(self):
        from apps.accounts.models import IPBlacklist
        from django.core.cache import cache
        cache.clear()
        IPBlacklist.objects.create(type='device', value='bad-device-hash', reason='Fraud')
        client = Client(REMOTE_ADDR='10.0.0.1', HTTP_X_DEVICE_HASH='bad-device-hash')
        response = client.get('/')
        assert response.status_code == 403

    def test_cidr_range_blocks_ip(self):
        from apps.accounts.models import IPBlacklist
        from django.core.cache import cache
        cache.clear()
        IPBlacklist.objects.create(type='cidr', value='172.16.0.0/16', reason='Range ban')
        client = Client(REMOTE_ADDR='172.16.5.10')
        response = client.get('/')
        assert response.status_code == 403


# ============================================================
# 3. IP SPOOFING DETECTION TESTS
# ============================================================

@pytest.mark.django_db
class TestIPSpoofingDetection:
    """Tests IP spoofing via header manipulation [EX-01.03]."""

    def test_suspicious_header_blocked(self):
        from apps.core.security_middleware import SecurityMiddleware
        factory = RequestFactory()
        # Set a suspicious header
        request = factory.get('/api/v1/tracks/', HTTP_X_ORIGINATING_IP='1.2.3.4')
        request.user = type('User', (), {'is_authenticated': False, 'is_staff': False})()
        mw = SecurityMiddleware(get_response=lambda r: JsonResponse({'ok': True}))
        response = mw(request)
        assert response.status_code == 403

    def test_excessive_xff_proxies_blocked(self):
        from apps.core.security_middleware import SecurityMiddleware
        factory = RequestFactory()
        xff = '1.1.1.1, 2.2.2.2, 3.3.3.3, 4.4.4.4, 5.5.5.5'
        request = factory.get('/api/v1/tracks/', HTTP_X_FORWARDED_FOR=xff)
        request.user = type('User', (), {'is_authenticated': False, 'is_staff': False})()
        mw = SecurityMiddleware(get_response=lambda r: JsonResponse({'ok': True}))
        response = mw(request)
        assert response.status_code == 403


# ============================================================
# 4. DOWNLOAD RATE LIMITING TESTS
# ============================================================

@pytest.mark.django_db
class TestDownloadRateLimiting:
    """Tests rapid download detection [EX-02.01]."""

    def test_rate_limiting_after_10_requests(self):
        from apps.core.security_middleware import SecurityMiddleware
        from django.core.cache import cache
        cache.clear()
        factory = RequestFactory()

        mw = SecurityMiddleware(get_response=lambda r: JsonResponse({'ok': True}))

        # First 10 should pass
        for i in range(10):
            request = factory.get('/download/token123', REMOTE_ADDR='10.5.5.5')
            request.user = type('User', (), {'is_authenticated': False, 'is_staff': False})()
            response = mw(request)

        # 11th should be rate limited
        request = factory.get('/download/token123', REMOTE_ADDR='10.5.5.5')
        request.user = type('User', (), {'is_authenticated': False, 'is_staff': False})()
        response = mw(request)
        assert response.status_code == 429


# ============================================================
# 5. ACCOUNT VELOCITY TESTS
# ============================================================

@pytest.mark.django_db
class TestAccountVelocity:
    """Tests API velocity limiting per user [EX-02.02]."""

    def test_velocity_limit_after_100_requests(self):
        from apps.core.security_middleware import AccountVelocityMiddleware
        from apps.accounts.models import User
        from django.core.cache import cache
        cache.clear()
        factory = RequestFactory()

        u = User.objects.create_user(email='velocity@example.com', password='Pass123!')
        mw = AccountVelocityMiddleware(get_response=lambda r: JsonResponse({'ok': True}))

        # Simulate 100 requests
        for i in range(100):
            request = factory.get('/api/v1/tracks/')
            request.user = u
            mw(request)

        # 101st should be throttled
        request = factory.get('/api/v1/tracks/')
        request.user = u
        response = mw(request)
        assert response.status_code == 429


# ============================================================
# 6. AUTH ENFORCEMENT TESTS
# ============================================================

@pytest.mark.django_db
class TestAuthEnforcement:
    """Tests authentication required on protected pages."""

    def test_dashboard_requires_login(self):
        client = Client()
        response = client.get('/dashboard/')
        assert response.status_code in [302, 301]  # Redirect to login

    def test_logout_clears_session(self):
        from apps.accounts.models import User
        User.objects.create_user(email='logout@example.com', password='StrongPass123!')
        client = Client()
        client.post('/login/', {'email': 'logout@example.com', 'password': 'StrongPass123!'})

        response = client.get('/logout/')
        assert response.status_code == 302
        # Session should be cleared
        response = client.get('/dashboard/')
        assert response.status_code in [302, 301]

    def test_signup_rejects_disposable_email(self):
        client = Client()
        response = client.post('/signup/', {
            'full_name': 'Hacker',
            'email': 'hacker@mailinator.com',
            'password': 'StrongPass123!',
        })
        assert response.status_code == 200  # Should stay on signup with error

    def test_signup_rejects_weak_password(self):
        client = Client()
        response = client.post('/signup/', {
            'full_name': 'Weak User',
            'email': 'weak@example.com',
            'password': 'weak',
        })
        assert response.status_code == 200  # Should stay on signup with error

    def test_duplicate_email_rejected(self):
        from apps.accounts.models import User
        User.objects.create_user(email='exists@example.com', password='StrongPass123!')
        client = Client()
        response = client.post('/signup/', {
            'full_name': 'Dup User',
            'email': 'exists@example.com',
            'password': 'StrongPass123!',
        })
        assert response.status_code == 200  # Stays on signup

    def test_admin_api_requires_staff(self):
        from apps.accounts.models import User
        User.objects.create_user(email='nonadmin@example.com', password='Pass123!')
        client = Client()
        client.login(email='nonadmin@example.com', password='Pass123!')
        response = client.get('/api/v1/accounts/users/')
        assert response.status_code in [401, 403]


# ============================================================
# 7. CSRF ENFORCEMENT TESTS
# ============================================================

@pytest.mark.django_db
class TestCSRFEnforcement:
    """Test CSRF token enforcement on POST endpoints."""

    def test_login_without_csrf_fails_for_browser(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        response = client.post('/login/', {
            'email': 'csrf@example.com',
            'password': 'Pass123!',
        })
        assert response.status_code == 403  # CSRF forbidden

    def test_signup_without_csrf_fails_for_browser(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        response = client.post('/signup/', {
            'full_name': 'CSRF User',
            'email': 'csrf@example.com',
            'password': 'StrongPass123!',
        })
        assert response.status_code == 403


# ============================================================
# 8. WEBHOOK SECURITY TESTS
# ============================================================

@pytest.mark.django_db
class TestWebhookSecurity:
    """Tests PhonePe webhook signature verification [BUG-001]."""

    def test_valid_signature_accepted(self):
        import hashlib
        from apps.payments.phonepe import PhonePeGateway
        gw = PhonePeGateway()
        payload = "eyJ0ZXN0IjoidmFsaWQifQ=="
        data = payload + gw.salt_key
        expected = hashlib.sha256(data.encode()).hexdigest() + "###" + gw.salt_index
        assert gw.verify_payment(payload, expected) is True

    def test_invalid_signature_rejected(self):
        from apps.payments.phonepe import PhonePeGateway
        gw = PhonePeGateway()
        assert gw.verify_payment("payload", "invalid###1") is False

    def test_empty_signature_rejected(self):
        from apps.payments.phonepe import PhonePeGateway
        gw = PhonePeGateway()
        assert gw.verify_payment("payload", "") is False

    def test_none_signature_rejected(self):
        from apps.payments.phonepe import PhonePeGateway
        gw = PhonePeGateway()
        assert gw.verify_payment("payload", None) is False

    def test_tampered_payload_rejected(self):
        import hashlib
        from apps.payments.phonepe import PhonePeGateway
        gw = PhonePeGateway()
        original = "eyJ0ZXN0IjoiYSJ9"
        tampered = "eyJ0ZXN0IjoiYiJ9"
        sig = hashlib.sha256((original + gw.salt_key).encode()).hexdigest() + "###" + gw.salt_index
        assert gw.verify_payment(tampered, sig) is False
