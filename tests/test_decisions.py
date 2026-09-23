"""Append-only test additions for preview/offer/support decisions."""

import pytest


@pytest.mark.django_db
class TestPreviewAndOfferDecisions:
    def test_dual_previews_accepted_and_embedded(self, client, track):
        track.youtube_url = "https://youtube.com/watch?v=abc123"
        track.instagram_url = "https://instagram.com/reel/xyz789/"
        track.preview_type = "youtube"
        track.save()
        resp = client.get(f"/tracks/{track.id}/")
        assert resp.status_code == 200
        html = resp.content.decode()
        assert "Preview 1" in html and "Preview 2" in html
        assert "youtube.com/embed" in html and "instagram.com" in html

    def test_dj_offer_banner_on_track_and_storefront(self, client, track, dj_user):
        from apps.admin_panel.models import PromotionalOffer

        _, dj = dj_user
        PromotionalOffer.objects.create(
            is_active=True,
            title="DJ Diwali Dhamaka",
            tagline="20% off this week",
            badge_label="DJ OFFER",
            dj=dj,
        )
        t_resp = client.get(f"/tracks/{track.id}/")
        assert t_resp.status_code == 200
        assert "DJ Diwali Dhamaka" in t_resp.content.decode()
        s_resp = client.get(f"/dj/{dj.slug}/")
        assert s_resp.status_code == 200
        assert "DJ Diwali Dhamaka" in s_resp.content.decode()

    def test_faq_about_asset_pages_load(self, client, user):
        for url in ("/legal/faq/", "/legal/about/", "/tracks/asset-pack/"):
            assert client.get(url).status_code == 200
        client.force_login(user)
        pdf = client.get("/tracks/asset-pack/handbook.pdf")
        assert pdf.status_code == 200
        assert pdf["Content-Type"] == "application/pdf"

    def test_support_ticket_and_telegram_link(self, client, user):
        client.force_login(user)
        resp = client.post(
            "/api/v1/platform/support/ticket/",
            {"subject": "Download stuck", "description": "Need help", "category": "download"},
            content_type="application/json",
        )
        assert resp.status_code == 201, resp.content[:300]
        body = resp.json()
        assert "telegram_url" in body and "t.me" in body["telegram_url"]

    def test_verify_source_link_action(self, client, dj_user):
        from unittest.mock import patch as _patch

        u, _ = dj_user
        client.force_login(u)
        with _patch("apps.downloads.source_fetch.probe_source", return_value=(True, "Link OK")):
            resp = client.post(
                "/api/v1/tracks/verify-source-link/",
                {"source_url": "https://drive.google.com/file/d/ABC/view"},
                content_type="application/json",
            )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
