"""
UI regressions found in the September 2026 audit: raw template text shown to users,
broken layouts from unbalanced tags, missing covers, jargon labels, wrong numbers.
"""

import re
from decimal import Decimal
from html.parser import HTMLParser

import pytest
from django.test import Client

CHECK = {"div", "section", "main", "form", "nav", "header", "footer", "aside", "article", "ul", "table"}


class _Balance(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag in CHECK:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag not in CHECK:
            return
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append(f"unexpected </{tag}> (open: {self.stack[-3:]})")


def _assert_clean(html):
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)
    assert not re.search(r"\{\{|\{%", text), "raw Django template syntax is visible on the page"
    p = _Balance()
    p.feed(html)
    assert not p.errors, p.errors[:3]
    assert not p.stack, f"unclosed tags: {p.stack[-5:]}"


@pytest.mark.django_db
class TestPagesRenderCleanly:
    @pytest.mark.parametrize(
        "path", ["/", "/releases/", "/djs/", "/login/", "/signup/", "/contact/", "/legal/terms/", "/legal/faq/"]
    )
    def test_public_pages(self, client, track, album, path):
        r = client.get(path)
        assert r.status_code == 200
        _assert_clean(r.content.decode())

    def test_detail_pages(self, client, track, album):
        for path in (f"/tracks/{track.id}/", f"/albums/{album.id}/", "/dj/test-dj/"):
            r = client.get(path)
            assert r.status_code == 200, path
            _assert_clean(r.content.decode())

    def test_logged_in_pages(self, track, album, dj_user, user):
        dj = Client()
        dj.force_login(dj_user[0])
        for path in ("/dashboard/dj/", "/upload/", "/dashboard/bundles/"):
            r = dj.get(path)
            assert r.status_code == 200, path
            _assert_clean(r.content.decode())
        buyer = Client()
        buyer.force_login(user)
        for path in ("/dashboard/", "/library/", "/cart/"):
            r = buyer.get(path)
            assert r.status_code == 200, path
            _assert_clean(r.content.decode())


@pytest.mark.django_db
class TestContent:
    def test_album_page_shows_cover_and_price(self, client, album):
        album.cover_image = "https://cdn.example.com/cover.jpg"
        album.save()
        html = client.get(f"/albums/{album.id}/").content.decode()
        assert 'src="https://cdn.example.com/cover.jpg"' in html
        assert "₹499" in html and "album.price" not in html
        assert "~0" not in html  # no made-up size estimate

    def test_free_track_says_free(self, client, track):
        track.price = Decimal("0.00")
        track.save()
        html = client.get(f"/tracks/{track.id}/").content.decode()
        assert "Free" in html and "₹0" not in html

    def test_no_jargon_labels_in_footer(self, client):
        html = client.get("/").content.decode()
        for jargon in ("Browse_Vault", "Support_Node", "Cycle_Theme", "Secure_Vault", "Privacy_Protocol"):
            assert jargon not in html

    def test_upload_page_shows_real_dj_share(self, dj_user):
        c = Client()
        c.force_login(dj_user[0])
        html = c.get("/upload/").content.decode()
        assert re.search(r"You keep \d+(\.\d)?% of every sale", html)

    def test_dj_dashboard_shows_wallet_earnings_and_sales(self, dj_user, track, user):
        from apps.commerce.models import Purchase
        from apps.commerce.services import MonetizationService

        p = Purchase.objects.create(
            user=user.profile, content_id=track.id, content_type="track", original_price=track.price,
            price_paid=track.price, seller=dj_user[1], status="paid", gateway_order_id="UI1",
        )
        MonetizationService.complete_purchase(p)
        c = Client()
        c.force_login(dj_user[0])
        r = c.get("/dashboard/dj/")
        assert r.context["total_sales"] == 1
        assert r.context["lifetime_earnings"] > 0


def test_money_filter_formats():
    from apps.tracks.templatetags.tracks_filters import initials, money, price_label

    assert money(Decimal("99.00")) == "₹99"
    assert money(Decimal("1299")) == "₹1,299"
    assert money(Decimal("49.5")) == "₹49.50"
    assert price_label(Decimal("0")) == "Free"
    assert price_label(Decimal("149")) == "₹149"
    assert initials("Aurora Pulse") == "AP"
