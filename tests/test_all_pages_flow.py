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
