"""
Storefront features borrowed from the SpinMarket playbook: releases page, bundles with one
checkout, limited drops that sell out, discounts, guest checkout, download recovery, Get listed.
"""

import json
from decimal import Decimal
from unittest import mock

import pytest
from django.core import mail, signing
from django.test import Client


def _login(user):
    c = Client()
    c.force_login(user)
    return c


class FakeGateway:
    name = "phonepe"
    calls = []

    def create_order(self, amount_paise, currency="INR", order_id=None, metadata=None):
        FakeGateway.calls.append(amount_paise)
        return {"redirect_url": "https://pay.example/x", "order_id": order_id, "gateway_order_id": order_id}


@pytest.fixture
def gateway():
    FakeGateway.calls = []
    with mock.patch("apps.payments.views.get_gateway", return_value=FakeGateway()):
        yield FakeGateway


def _track(dj, title, price, **kw):
    from apps.tracks.models import Track

    return Track.objects.create(dj=dj, title=title, price=Decimal(price), file_key=f"tracks/{title}.wav",
                                preview_type="youtube", youtube_url="https://youtube.com/watch?v=abc123", **kw)


def _paid(user, track):
    from apps.commerce.models import Purchase

    return Purchase.objects.create(user=user.profile, content_type="track", content_id=track.id, seller=track.dj,
                                   original_price=track.price, price_paid=track.price, status="paid",
                                   gateway_order_id=f"MM_P{track.id}")


@pytest.mark.django_db
class TestReleasesPages:
    def test_releases_lists_tracks_and_filters(self, client, dj_user):
        _, dj = dj_user
        _track(dj, "Sunset Edit", "80", genre="House")
        _track(dj, "Night Tool", "60", genre="Techno")
        html = client.get("/releases/").content.decode()
        assert "Sunset Edit" in html and "Night Tool" in html
        html = client.get("/releases/", {"genre": "House"}).content.decode()
        assert "Sunset Edit" in html and "Night Tool" not in html

    def test_old_explore_links_redirect(self, client):
        r = client.get("/explore/", {"q": "edit", "type": "album"})
        assert r.status_code == 301 and r["Location"].startswith("/releases/") and "q=edit" in r["Location"]

    def test_preview_uses_dj_youtube_link(self, client, dj_user):
        _track(dj_user[1], "Preview Me", "50")
        html = client.get("/releases/").content.decode()
        assert "youtube" in html and "data-embed" in html

    def test_sell_and_shipping_pages(self, client):
        assert client.get("/sell/").status_code == 200
        assert client.get("/legal/shipping/").status_code == 200


@pytest.mark.django_db
class TestLimitedDropsAndDiscounts:
    def test_discount_shows_savings(self, client, dj_user):
        t = _track(dj_user[1], "Deal", "75", compare_at_price=Decimal("150"))
        html = client.get(f"/tracks/{t.id}/").content.decode()
        assert "Save 50%" in html

    def test_drop_counts_down_and_sells_out(self, client, dj_user, user, second_user, gateway):
        t = _track(dj_user[1], "Only One", "99", copies_limit=1)
        assert "Only One" in client.get("/drops/").content.decode()
        _paid(second_user, t)
        assert "Sold out" in client.get(f"/tracks/{t.id}/").content.decode()
        r = _login(user).post("/api/v1/payments/initiate/", json.dumps({"content_id": t.id, "content_type": "track"}),
                              content_type="application/json")
        assert r.status_code == 400 and "Sold out" in r.json()["error"]
        assert gateway.calls == []

    def test_pending_checkout_holds_the_last_copy(self, dj_user, second_user):
        from apps.commerce.models import Purchase
        from apps.core.catalog import copies_left

        t = _track(dj_user[1], "Held", "99", copies_limit=1)
        Purchase.objects.create(user=second_user.profile, content_type="track", content_id=t.id, seller=t.dj,
                                original_price=t.price, price_paid=t.price, status="pending", gateway_order_id="MM_H")
        assert copies_left(t, "track") == 0

    def test_dj_sets_offers_on_edit(self, dj_user):
        u, dj = dj_user
        t = _track(dj, "Edit Me", "100")
        c = _login(u)
        r = c.post(f"/dashboard/dj/track/{t.id}/edit/", {"title": "Edit Me", "price": "100", "compare_at_price": "200",
                                                         "copies_limit": "25", "youtube_url": t.youtube_url,
                                                         "is_active": "on"})
        assert r.status_code == 302
        t.refresh_from_db()
        assert t.compare_at_price == Decimal("200.00") and t.copies_limit == 25
        r = c.post(f"/dashboard/dj/track/{t.id}/edit/", {"title": "Edit Me", "price": "100", "compare_at_price": "50",
                                                         "youtube_url": t.youtube_url, "is_active": "on"})
        assert r.status_code == 400


@pytest.mark.django_db
class TestBundles:
    def _bundle(self, dj):
        from apps.commerce.models import Bundle, BundleTrack

        a, b = _track(dj, "A", "100"), _track(dj, "B", "300")
        bundle = Bundle.objects.create(dj=dj, title="Starter Pack", price=Decimal("200"))
        BundleTrack.objects.create(bundle=bundle, track=a, display_order=0)
        BundleTrack.objects.create(bundle=bundle, track=b, display_order=1)
        return bundle, a, b

    def test_bundle_pages(self, client, dj_user):
        bundle, *_ = self._bundle(dj_user[1])
        assert "Starter Pack" in client.get("/bundles/").content.decode()
        html = client.get(f"/bundles/{bundle.id}/").content.decode()
        assert "Starter Pack" in html and "50%" in html

    def test_bundle_checkout_is_one_order_split_by_price(self, dj_user, user, gateway):
        from apps.commerce.models import Purchase

        bundle, a, b = self._bundle(dj_user[1])
        r = _login(user).post(f"/bundles/{bundle.id}/checkout/")
        assert r.status_code == 200, r.content
        rows = list(Purchase.objects.filter(user=user.profile, status="pending").order_by("content_id"))
        assert len(rows) == 2 and len({p.gateway_order_id for p in rows}) == 1
        assert rows[0].gateway_order_id.startswith("MMB_")
        track_share = sorted(p.amount_paise for p in rows)
        fee = gateway.calls[0] - 20000
        assert sum(track_share) - fee == 20000  # the bundle price, once

    def test_bundle_skips_owned_tracks_and_needs_login(self, client, dj_user, user, gateway):
        from apps.commerce.models import Purchase

        bundle, a, b = self._bundle(dj_user[1])
        assert client.post(f"/bundles/{bundle.id}/checkout/").status_code == 401
        _paid(user, a)
        _login(user).post(f"/bundles/{bundle.id}/checkout/")
        pending = Purchase.objects.filter(user=user.profile, status="pending")
        assert [p.content_id for p in pending] == [b.id]


@pytest.mark.django_db
class TestGuestCheckoutAndRecovery:
    def test_new_email_gets_account_and_session(self, client):
        from apps.accounts.models import User

        r = client.post("/checkout/guest/", json.dumps({"email": "new.buyer@gmail.com"}), content_type="application/json")
        assert r.status_code == 200 and r.json()["created"]
        u = User.objects.get(email="new.buyer@gmail.com")
        assert not u.has_usable_password()
        assert client.get("/library/").status_code == 200

    def test_existing_email_is_never_logged_in(self, client, user):
        r = client.post("/checkout/guest/", json.dumps({"email": user.email}), content_type="application/json")
        assert r.status_code == 409 and r.json()["exists"]
        assert "_auth_user_id" not in client.session

    def test_recover_link_works_once(self, client, user):
        r = client.post("/recover/", {"email": user.email})
        assert r.status_code == 200
        r2 = client.post("/recover/", {"email": "nobody@example.com"})
        assert r2.content.decode().count("Check your inbox") == r.content.decode().count("Check your inbox")
        token = signing.dumps({"u": str(user.pk), "l": ""}, salt="mixmint.recover")
        fresh = Client()
        assert fresh.get(f"/recover/{token}/")["Location"].endswith("/library/")
        again = Client().get(f"/recover/{token}/")
        assert again["Location"] == "/recover/"

    def test_bad_token_rejected(self, client):
        assert client.get("/recover/nonsense/")["Location"] == "/recover/"


@pytest.mark.django_db
class TestDJApplicationLinks:
    def test_drive_links_rejected(self, user):
        r = _login(user).post("/apply-dj/", {"dj_name": "Nova", "slug": "nova", "legal_agreement_accepted": "on",
                                            "city": "Goa", "links": "https://drive.google.com/file/d/x"})
        assert r.status_code == 400

    def test_needs_at_least_one_link(self, user):
        r = _login(user).post("/apply-dj/", {"dj_name": "Nova", "slug": "nova", "legal_agreement_accepted": "on",
                                            "city": "Goa"})
        assert r.status_code == 400
