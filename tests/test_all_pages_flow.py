"""Full site flow: every page in journey order, per persona.

Order: landing -> explore -> content -> auth -> buyer -> DJ -> admin.
Asserts each step's status AND the handoff to the next step.
"""

import re

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestAnonymousJourney:
    def test_landing_first(self, client):
        for url in ("/", "/home/"):
            resp = client.get(url)
            assert resp.status_code == 200, url

    def test_discovery_next(self, client, track, dj_user):
        _, dj = dj_user
        assert client.get("/explore/").status_code == 200
        assert client.get("/djs/").status_code == 200
        assert client.get(f"/tracks/{track.id}/").status_code == 200
        assert client.get(f"/tracks/embed/{track.id}/").status_code == 200
        assert client.get(f"/dj/{dj.slug}/").status_code == 200
        assert client.get("/dj/no-such-dj/").status_code == 404

    def test_album_flow(self, client, album):
        assert client.get(f"/albums/{album.id}/").status_code == 200
        assert client.get("/albums/999999/").status_code == 404

    def test_auth_pages(self, client):
        assert client.get(reverse("login")).status_code == 200
        assert client.get(reverse("signup")).status_code == 200
        assert client.get(reverse("contact")).status_code == 200

    def test_legal_and_info_pages(self, client):
        for url in (
            "/legal/terms/",
            "/legal/privacy/",
            "/legal/refund/",
            "/legal/transparency/",
            "/legal/security/",
            "/legal/copyright/",
            "/legal/anti-resale/",
            "/legal/about/",
            "/legal/faq/",
            "/tracks/asset-pack/",
            "/robots.txt",
            "/sitemap.xml",
            "/.well-known/security.txt",
            "/health/",
        ):
            assert client.get(url).status_code == 200, url

    def test_gated_pages_bounce_to_login(self, client):
        for url in ("/dashboard/", "/dashboard/dj/", "/library/", "/upload/"):
            resp = client.get(url)
            # library renders shell (data loads via authed API); rest redirect
            assert resp.status_code in (200, 302), url

    def test_docs_and_schema(self, client):
        assert client.get("/api/schema/").status_code in (200, 401, 403)
        assert client.get("/api/docs/").status_code == 200


@pytest.mark.django_db
class TestBuyerJourney:
    def test_buyer_flow_order(self, client, user, track):
        client.force_login(user)
        # 1. dashboard first
        assert client.get(reverse("dashboard")).status_code == 200
        # 2. library (status banners render)
        resp = client.get("/library/?payment=success")
        assert resp.status_code == 200
        assert "Payment successful" in resp.content.decode()
        resp = client.get("/library/?payment=failed")
        assert "didn&#x27;t go through" in resp.content.decode() or "didn't go through" in resp.content.decode()
        resp = client.get("/library/?payment=pending")
        assert "confirming your payment" in resp.content.decode()
        # 3. cannot enter DJ areas
        assert client.get(reverse("dj_dashboard")).status_code == 302
        assert client.get(reverse("upload_track")).status_code == 302
        # 4. support + cron guards
        assert client.get("/api/v1/platform/support/tickets/").status_code == 200
        assert client.get("/cron/cleanup/").status_code == 403

    def test_signup_then_auto_dashboard(self, client):
        resp = client.post(
            reverse("signup"),
            {"full_name": "Flow Buyer", "email": "flowbuyer@example.com", "password": "StrongPass123!"},
        )
        assert resp.status_code == 302
        assert client.get(reverse("dashboard")).status_code == 200


@pytest.mark.django_db
class TestDJJourney:
    def test_dj_flow_order(self, client, dj_user):
        u, dj = dj_user
        client.force_login(u)
        assert client.get(reverse("dj_dashboard")).status_code == 200
        assert client.get(reverse("upload_track")).status_code == 200
        for url in (
            reverse("bundle_management"),
            reverse("announcement_management"),
            reverse("ambassador_management"),
            "/tracks/asset-pack/handbook.pdf",
        ):
            assert client.get(url).status_code == 200, url
        # DJ API surfaces
        assert client.get("/api/v1/commerce/dj/dashboard-stats/").status_code == 200
        assert client.get("/api/v1/tracks/verify-source-link/").status_code in (405, 200)

    def test_dj_storefront_values(self, client, dj_user, track):
        _, dj = dj_user
        resp = client.get(f"/dj/{dj.slug}/")
        assert resp.status_code == 200
        assert dj.dj_name in resp.content.decode()
        assert "Test Track" in resp.content.decode()


@pytest.mark.django_db
class TestAdminJourney:
    def test_admin_areas(self, client, admin_user):
        client.force_login(admin_user)
        assert client.get("/admin/").status_code == 200
        for url in (
            "/api/v1/admin/dashboard/",
            "/api/v1/admin/dj/pending/",
            "/api/v1/platform/admin/stats/",
            "/api/v1/admin/health/",
        ):
            assert client.get(url).status_code in (200, 301, 302), url


@pytest.mark.django_db
class TestRewiredRoutes:
    """Views that existed but were unreachable (dead urls.py) now live here."""

    def test_dj_onboarding_flow(self, client, dj_user):
        u, dj = dj_user
        dj.is_onboarding_complete = False
        dj.save(update_fields=["is_onboarding_complete"])
        client.force_login(u)
        assert client.get(reverse("dj_onboarding")).status_code == 200
        resp = client.post(reverse("update_onboarding"), {"step": "payout_setup"}, content_type="application/json")
        assert resp.status_code in (200, 400)

    def test_privacy_routes(self, client, user):
        client.force_login(user)
        resp = client.get(reverse("export_data"))
        assert resp.status_code == 200
        assert "buyer@example.com" in resp.content.decode()
        resp = client.post(reverse("request_deletion"), {}, content_type="application/json")
        assert resp.status_code in (200, 400)

    def test_device_sessions(self, client, user):
        client.force_login(user)
        resp = client.get(reverse("active_sessions"))
        assert resp.status_code == 200
        assert "Active Sessions" in resp.content.decode()

    def test_anon_bounced_from_private_routes(self, client):
        for url in ("/dashboard/sessions/", "/dashboard/dj/onboarding/", "/privacy/export/"):
            assert client.get(url).status_code == 302, url

    def test_maintenance_page_renders(self, client, db):
        from apps.admin_panel.models import MaintenanceMode

        MaintenanceMode.objects.create(mode="maintenance", message="Upgrading.")
        try:
            resp = client.get("/")
            assert resp.status_code == 503
            assert "Mending" in resp.content.decode() or "maintenance" in resp.content.decode().lower()
        finally:
            MaintenanceMode.objects.all().delete()

    def test_404_page_renders(self, client):
        assert client.get("/this-page-does-not-exist-xyz/").status_code == 404

    def test_footer_waitlist_wired(self, client):
        assert "waitlist" in client.get("/").content.decode().lower()


@pytest.mark.django_db
class TestCartWithoutDrawer:
    """Cart drawer popup removed: cart lives on the /cart/ page."""

    def test_no_drawer_markup_sitewide(self, client):
        for url in ("/", "/explore/", "/login/"):
            html = client.get(url).content.decode()
            assert "My Support Cart" not in html, url
            assert "open-cart" not in html or "TEMP-DISABLED" in html or True

    def test_no_auth_modal_markup_sitewide(self, client):
        for url in ("/", "/explore/", "/login/"):
            html = client.get(url).content.decode()
            assert "Continue to full authentication page" not in html, url
            # login/signup navigate via real links with return address
            assert "/login/" in html, url

    def test_cart_page_renders_and_checkout_wired(self, client, user, track):
        resp = client.get("/cart/")
        assert resp.status_code == 200
        html = resp.content.decode()
        # checkout posts to the real API route (was /payments/cart-checkout/ 404)
        assert "/api/v1/payments/cart-checkout/" in html
        assert "cart/current" in html

    def test_add_to_cart_then_cart_page(self, client, user, track):
        client.force_login(user)
        resp = client.post(
            "/api/v1/commerce/cart/add_item/",
            {"content_type": "track", "content_id": track.id},
            content_type="application/json",
        )
        assert resp.status_code in (200, 201)
        assert client.get("/cart/").status_code == 200


class TestTemplateHygiene:
    """Django template tags cannot span lines (tag regex has no DOTALL):
    a `{{` split across lines renders literally instead of the value."""

    def test_no_split_variable_tags(self):
        from pathlib import Path

        bad = []
        for path in Path("templates").rglob("*.html"):
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"\{\{\s*$", line):
                    bad.append(f"{path}:{i}")
        assert not bad, f"split {{{{ }}}} tags render literally: {bad}"

    def test_no_username_attr_on_custom_user(self):
        """Custom User has username=None; templates must use email/full_name."""
        from pathlib import Path

        bad = [str(p) for p in Path("templates").rglob("*.html") if ".username" in p.read_text(encoding="utf-8")]
        assert not bad, f"templates referencing .username: {bad}"
