"""Login as every user type: buyer, DJ, Pro DJ, admin + frozen/banned/wrong-pw.

Covers the full browser login (POST /login/) the stuck-modal users hit.
"""

import pytest
from django.urls import reverse


def _post_login(client, email, password, next_url=None):
    url = reverse("login")
    if next_url:
        url += f"?next={next_url}"
    return client.post(url, {"email": email, "password": password})


@pytest.mark.django_db
class TestBuyerLogin:
    def test_buyer_login_lands_on_dashboard(self, client, user):
        resp = _post_login(client, "buyer@example.com", "StrongPass123!")
        assert resp.status_code == 302
        assert resp["Location"].endswith(reverse("dashboard"))
        dash = client.get(reverse("dashboard"))
        assert dash.status_code == 200

    def test_buyer_cannot_use_dj_dashboard(self, client, user):
        _post_login(client, "buyer@example.com", "StrongPass123!")
        resp = client.get(reverse("dj_dashboard"))
        assert resp.status_code == 302
        assert resp["Location"].endswith(reverse("dashboard"))

    def test_login_records_history_and_ip_binding(self, client, user):
        from apps.accounts.models import LoginHistory

        _post_login(client, "buyer@example.com", "StrongPass123!")
        assert LoginHistory.objects.filter(user=user).exists()
        assert client.session.get("bound_ip") is not None

    def test_honors_safe_next_url(self, client, user):
        resp = _post_login(client, "buyer@example.com", "StrongPass123!", next_url="/explore/")
        assert resp.status_code == 302
        assert resp["Location"].endswith("/explore/")

    def test_honors_next_from_post_body(self, client, user):
        # Real browser flow: modal GETs /login/?next=.., form POSTs hidden field.
        page = client.get(reverse("login") + "?next=/explore/")
        assert page.status_code == 200
        assert 'name="next"' in page.content.decode()
        resp = client.post(
            reverse("login"), {"email": "buyer@example.com", "password": "StrongPass123!", "next": "/explore/"}
        )
        assert resp.status_code == 302
        assert resp["Location"].endswith("/explore/")

    def test_rejects_evil_next_url(self, client, user):
        resp = _post_login(client, "buyer@example.com", "StrongPass123!", next_url="https://evil.com/steal")
        assert resp.status_code == 302
        assert "evil.com" not in resp["Location"]
        assert resp["Location"].endswith(reverse("dashboard"))


@pytest.mark.django_db
class TestDJLogin:
    def test_dj_reaches_dj_dashboard(self, client, dj_user):
        u, dj = dj_user
        resp = _post_login(client, "dj@example.com", "DJPass123!")
        assert resp.status_code == 302
        assert client.get(reverse("dj_dashboard")).status_code == 200

    def test_pro_dj_login_and_pro_flag(self, client, pro_dj_user):
        u, dj = pro_dj_user
        _post_login(client, "prodj@example.com", "ProDJ123!")
        u.profile.refresh_from_db()
        assert u.profile.is_pro_dj is True
        assert client.get(reverse("dj_dashboard")).status_code == 200


@pytest.mark.django_db
class TestAdminLogin:
    def test_admin_reaches_django_admin(self, client, admin_user):
        _post_login(client, "admin@mixmint.site", "AdminPass123!")
        resp = client.get("/admin/")
        assert resp.status_code == 200

    def test_nonstaff_blocked_from_django_admin(self, client, user):
        _post_login(client, "buyer@example.com", "StrongPass123!")
        resp = client.get("/admin/")
        assert resp.status_code == 302  # redirected to admin login, not admitted


@pytest.mark.django_db
class TestLoginFailures:
    def test_wrong_password_stays_on_login(self, client, user):
        resp = _post_login(client, "buyer@example.com", "WrongPass999!")
        assert resp.status_code == 200
        assert "_auth_user_id" not in client.session

    def test_unknown_email_stays_on_login(self, client, db):
        resp = _post_login(client, "ghost@example.com", "Whatever123!")
        assert resp.status_code == 200
        assert "_auth_user_id" not in client.session

    def test_frozen_account_cannot_login(self, client, user):
        user.profile.is_frozen = True
        user.profile.save(update_fields=["is_frozen"])
        resp = _post_login(client, "buyer@example.com", "StrongPass123!")
        assert resp.status_code == 200
        assert "_auth_user_id" not in client.session

    def test_banned_account_cannot_login(self, client, user):
        user.profile.is_banned = True
        user.profile.save(update_fields=["is_banned"])
        resp = _post_login(client, "buyer@example.com", "StrongPass123!")
        assert resp.status_code == 200
        assert "_auth_user_id" not in client.session

    def test_login_page_renders_with_modal_fallback(self, client):
        resp = client.get(reverse("login"))
        assert resp.status_code == 200
        html = resp.content.decode()
        # Login form posts to itself with email + password fields (no modal involved)
        assert 'name="email"' in html and 'name="password"' in html
        assert 'name="csrfmiddlewaretoken"' in html

    def test_logout_ends_session(self, client, user):
        _post_login(client, "buyer@example.com", "StrongPass123!")
        assert "_auth_user_id" in client.session
        client.get(reverse("logout"))
        assert "_auth_user_id" not in client.session
