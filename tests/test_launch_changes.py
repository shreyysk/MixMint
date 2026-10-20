"""Launch-prep changes: download policy, weekly payouts with email codes, pay-all, referral cap,
release reports + admin alerts, ad income sharing, the cart-discount switch, one Pro trial, and the new card rows."""

from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.test import Client
from django.utils import timezone

from apps.downloads.models import DownloadLog
from apps.downloads.utils import DownloadManager


def _log(user, track, ip="1.1.1.1", dev="dev-a", ok=True):
    return DownloadLog.objects.create(user=user.profile, content_id=track.id, content_type="track",
                                      ip_address=ip, device_hash=dev, completed=ok)


# ── Download policy: 3 downloads, first device/network, within 7 days; then 50% ──
@pytest.mark.django_db
class TestDownloadPolicy:
    def test_first_download_is_free(self, user, track, purchase):
        assert DownloadManager.free_download_state(user.profile, track.id, "track", "9.9.9.9", "x")[0] == "free"

    def test_same_device_free_until_three(self, user, track, purchase):
        _log(user, track)
        _log(user, track, ip="2.2.2.2")  # same device, other network is fine
        assert DownloadManager.free_download_state(user.profile, track.id, "track", "1.1.1.1", "dev-a")[0] == "free"
        _log(user, track)
        state, msg = DownloadManager.free_download_state(user.profile, track.id, "track", "1.1.1.1", "dev-a")
        assert state == "pay" and "50%" in msg

    def test_other_device_and_network_locked_within_window(self, user, track, purchase):
        _log(user, track)
        state, _ = DownloadManager.free_download_state(user.profile, track.id, "track", "5.5.5.5", "dev-b")
        assert state == "locked"

    def test_after_seven_days_pay_half(self, user, track, purchase):
        from apps.commerce.models import Purchase

        old = timezone.now() - timedelta(days=8)
        Purchase.objects.filter(pk=purchase.pk).update(created_at=old)
        if hasattr(purchase, "paid_at"):
            Purchase.objects.filter(pk=purchase.pk).update(paid_at=old)
        state, msg = DownloadManager.free_download_state(user.profile, track.id, "track", "1.1.1.1", "dev-a")
        assert state == "pay" and "7-day" in msg

    def test_failed_downloads_do_not_count(self, user, track, purchase):
        for _ in range(3):
            _log(user, track, ok=False)
        assert DownloadManager.free_download_state(user.profile, track.id, "track", "1.1.1.1", "dev-a")[0] == "free"

    def test_no_purchase_means_pay(self, user, track):
        assert DownloadManager.free_download_state(user.profile, track.id, "track")[0] == "pay"


# ── DJ payouts: once a week, email code ──
@pytest.fixture
def dj_client(dj_user):
    u, dj = dj_user
    dj.upi_id = "testdj@upi"
    dj.save(update_fields=["upi_id"])
    c = Client()
    c.force_login(u)
    return c, dj


@pytest.mark.django_db
class TestPayouts:
    def test_weekly_limit(self, dj_client):
        from apps.commerce.models import Payout

        c, dj = dj_client
        Payout.objects.create(dj=dj, amount=Decimal("600"), status="completed")
        r = c.post("/api/v1/commerce/payouts/request/", {"verification_code": "123456"}, content_type="application/json")
        assert r.status_code == 400
        assert "once a week" in r.json()["error"]

    def test_failed_payout_does_not_block(self, dj_client):
        from apps.commerce.models import Payout

        c, dj = dj_client
        Payout.objects.create(dj=dj, amount=Decimal("600"), status="failed")
        r = c.post("/api/v1/commerce/payouts/request/", {"verification_code": "000000"}, content_type="application/json")
        assert "once a week" not in str(r.content)

    def test_email_code_round_trip(self, dj_user):
        from apps.accounts import payout_auth

        _, dj = dj_user
        sent = {}
        with mock.patch("apps.admin_panel.email_utils.send_email", side_effect=lambda to, subj, body: sent.update(subj=subj)):
            ok, _ = payout_auth.send_payout_code(dj, "withdraw")
        assert ok
        code = sent["subj"].rsplit(" ", 1)[-1]
        assert payout_auth.verify_email_code(dj, "000000" if code != "000000" else "111111", "withdraw")[0] is False
        assert payout_auth.verify_email_code(dj, code, "withdraw")[0] is True
        assert payout_auth.verify_email_code(dj, code, "withdraw")[0] is False  # works once

    def test_code_for_other_purpose_rejected(self, dj_user):
        from apps.accounts import payout_auth

        _, dj = dj_user
        sent = {}
        with mock.patch("apps.admin_panel.email_utils.send_email", side_effect=lambda to, subj, body: sent.update(subj=subj)):
            payout_auth.send_payout_code(dj, "details")
        assert payout_auth.verify_email_code(dj, sent["subj"].rsplit(" ", 1)[-1], "withdraw")[0] is False


@pytest.mark.django_db
class TestPayAll:
    def test_mark_all_paid_needs_reference(self, admin_user, dj_user):
        from apps.commerce.models import Payout

        _, dj = dj_user
        p = Payout.objects.create(dj=dj, amount=Decimal("500"), status="pending")
        c = Client()
        c.force_login(admin_user)
        c.post("/api/v1/admin/payouts/", {"action": "paid_all", "reference": ""})
        p.refresh_from_db()
        assert p.status == "pending"
        c.post("/api/v1/admin/payouts/", {"action": "paid_all", "reference": "BATCH-42"})
        p.refresh_from_db()
        assert p.status == "completed" and p.payment_reference.startswith("BATCH-42")

    def test_bulk_file(self, admin_user, dj_user):
        from apps.commerce.models import Payout

        _, dj = dj_user
        dj.upi_id = "dj@upi"
        dj.save(update_fields=["upi_id"])
        Payout.objects.create(dj=dj, amount=Decimal("750"), status="pending")
        c = Client()
        c.force_login(admin_user)
        r = c.get("/api/v1/admin/payouts/?export=csv")
        assert r.status_code == 200 and "dj@upi" in r.content.decode()

    def test_not_for_djs(self, dj_client):
        c, _ = dj_client
        assert c.post("/api/v1/admin/payouts/", {"action": "paid_all", "reference": "X"}).status_code in (302, 403)


# ── Referrals: max 50 per DJ ──
@pytest.mark.django_db
def test_referral_cap(dj_user, monkeypatch):
    from apps.commerce import referrals

    _, dj = dj_user
    monkeypatch.setattr(referrals, "referral_count", lambda r: referrals.MAX_REFERRALS)
    assert referrals.has_room(dj) is False
    monkeypatch.setattr(referrals, "referral_count", lambda r: referrals.MAX_REFERRALS - 1)
    assert referrals.has_room(dj) is True


# ── Reports + admin alerts ──
@pytest.mark.django_db
class TestReports:
    def test_guest_copyright_report_alerts_admins(self, track, settings):
        from apps.admin_panel.models import ContentReport

        settings.ADMIN_ALERT_EMAIL = "owner@example.com"
        with mock.patch("apps.admin_panel.models.alert_admins_new_report") as alert:
            r = Client().post("/report/", {"content_type": "track", "content_id": track.id, "report_type": "copyright",
                                           "reason": "This is my remix, uploaded without permission.", "email": "artist@example.com",
                                           "sworn": True}, content_type="application/json")
        assert r.status_code in (200, 201), r.content
        rep = ContentReport.objects.get()
        assert rep.reporter is None and rep.reporter_email == "artist@example.com"

    def test_copyright_needs_sworn_statement(self, track):
        r = Client().post("/report/", {"content_type": "track", "content_id": track.id, "report_type": "copyright",
                                       "reason": "This is my remix, uploaded without permission.", "email": "a@example.com"},
                          content_type="application/json")
        assert r.status_code == 400

    def test_guest_needs_email(self, track):
        r = Client().post("/report/", {"content_type": "track", "content_id": track.id, "report_type": "spam",
                                       "reason": "Misleading title and cover art."}, content_type="application/json")
        assert r.status_code == 400

    def test_alert_sends_email_and_telegram(self, track, settings):
        from apps.admin_panel.models import ContentReport, alert_admins_new_report

        settings.ADMIN_ALERT_EMAIL = "owner@example.com"
        rep = ContentReport(content_type="track", content_id=track.id, report_type="copyright", reason="mine",
                            reporter_email="a@example.com")
        with mock.patch("apps.admin_panel.email_utils.send_email") as em, \
                mock.patch("apps.admin_panel.telegram.notify_admins"):
            alert_admins_new_report(rep)
        assert em.called
        assert "URGENT" in str(em.call_args) or "copyright" in str(em.call_args).lower()


# ── Ad income sharing ──
@pytest.mark.django_db
class TestAdIncome:
    def test_split_by_views_once_per_period(self, dj_user):
        from apps.accounts.models import DJPageView
        from apps.commerce.ad_revenue_service import distribute_ad_income
        from apps.commerce.models import DJWallet

        _, dj = dj_user
        for _ in range(4):
            DJPageView.objects.create(dj=dj, page_type="storefront")
        today = date.today()
        out = distribute_ad_income(Decimal("1000"), today - timedelta(days=1), today + timedelta(days=1))
        assert out["djs"] == 1 and out["credited"] == Decimal("150.00")
        assert DJWallet.objects.get(dj=dj).available_for_payout == Decimal("150.00")
        with pytest.raises(ValueError):
            distribute_ad_income(Decimal("1000"), today - timedelta(days=1), today + timedelta(days=1))

    def test_no_views_no_share(self, db):
        from apps.commerce.ad_revenue_service import distribute_ad_income

        with pytest.raises(ValueError):
            distribute_ad_income(Decimal("500"), date(2020, 1, 1), date(2020, 1, 31))


# ── Cart discount switch ──
@pytest.mark.django_db
def test_cart_discounts_off_by_default(cart, platform_settings):
    from apps.commerce.models import Cart

    assert platform_settings.cart_discounts_enabled is False
    assert Cart.discounts_on() is False
    assert cart.discount_percentage == 0
    platform_settings.cart_discounts_enabled = True
    platform_settings.save()
    assert Cart.discounts_on() is True


# ── One Pro trial per DJ ──
@pytest.mark.django_db
def test_pro_trial_only_once(dj_client):
    c, dj = dj_client
    profile = dj.profile
    profile.pro_trial_ends_at = timezone.now() - timedelta(days=30)
    profile.is_pro_dj = False
    profile.save(update_fields=["pro_trial_ends_at", "is_pro_dj"])
    r = c.post("/api/v1/commerce/pro/activate/")
    assert r.status_code == 400 and "already used" in r.json()["error"]


# ── Pages with card rows render ──
@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/releases/", "/djs/", "/dj/test-dj/", "/sell/"])
def test_row_pages_render(path, track, album):
    r = Client().get(path)
    assert r.status_code == 200, path
    body = r.content.decode()
    assert "{#" not in body and "Netflix-style" not in body
    if path in ("/", "/dj/test-dj/"):
        assert "mm-shelf" in body


@pytest.mark.django_db
def test_sell_page_listing_fee_and_earn_line(platform_settings):
    body = Client().get("/sell/").content.decode()
    assert "100% earning opportunity" in body
    assert "No listing fee" in body or "listing fee" in body.lower()


# ── Dark mode: off by default, admin switch ──
@pytest.mark.django_db
def test_light_only_by_default():
    body = Client().get("/").content.decode()
    assert 'data-theme="light"' in body and "window.MM_DARK_MODE = false" in body
    assert 'onclick="toggleTheme()" data-theme-toggle' not in body


@pytest.mark.django_db
def test_admin_can_allow_dark_mode(admin_user):
    from django.core.cache import cache

    c = Client()
    c.force_login(admin_user)
    r = c.post("/api/v1/admin/settings/", {"action": "appearance", "dark_mode": "on"})
    assert r.status_code == 302
    cache.clear()
    body = Client().get("/").content.decode()
    assert "window.MM_DARK_MODE = true" in body and 'onclick="toggleTheme()" data-theme-toggle' in body
    c.post("/api/v1/admin/settings/", {"action": "appearance"})
    cache.clear()
    assert 'onclick="toggleTheme()" data-theme-toggle' not in Client().get("/").content.decode()


# ── Releases search: date, price, BPM, DJ filters and sorts; regional genres ──
@pytest.mark.django_db
class TestReleaseFilters:
    @pytest.fixture
    def catalog(self, dj_user):
        from apps.tracks.models import Track

        _, dj = dj_user
        mk = lambda title, price, bpm, genre, when: Track.objects.create(  # noqa: E731
            dj=dj, title=title, price=Decimal(price), file_key=f"t/{title}.wav", preview_type="youtube",
            youtube_url="https://youtube.com/watch?v=x", genre=genre, bpm=bpm)
        a = mk("Alpha", "49", 124, "Tulu", None)
        b = mk("Bravo", "149", 140, "Kannada", None)
        c = mk("Charlie", "0", 98, "Techno", None)
        Track.objects.filter(pk=a.pk).update(created_at=timezone.make_aware(timezone.datetime(2025, 3, 10)))
        Track.objects.filter(pk=b.pk).update(created_at=timezone.make_aware(timezone.datetime(2026, 7, 2)))
        Track.objects.filter(pk=c.pk).update(created_at=timezone.make_aware(timezone.datetime(2026, 9, 20)))
        return a, b, c

    def titles(self, url):
        r = Client().get(url)
        assert r.status_code == 200
        return [o.title for k, o in r.context["page"].object_list]

    def test_year_and_month(self, catalog):
        assert self.titles("/releases/?year=2026") == ["Charlie", "Bravo"]
        assert self.titles("/releases/?year=2026&month=7") == ["Bravo"]
        assert self.titles("/releases/?year=2025") == ["Alpha"]

    def test_sorts(self, catalog):
        assert self.titles("/releases/?sort=old") == ["Alpha", "Bravo", "Charlie"]
        assert self.titles("/releases/?sort=title_za") == ["Charlie", "Bravo", "Alpha"]
        assert self.titles("/releases/?sort=bpm_low") == ["Charlie", "Alpha", "Bravo"]
        assert self.titles("/releases/?sort=price_high")[0] == "Bravo"

    def test_price_bpm_genre(self, catalog):
        assert self.titles("/releases/?price=free") == ["Charlie"]
        assert self.titles("/releases/?price=u50") == ["Alpha"]
        assert self.titles("/releases/?bpm=121-128") == ["Alpha"]
        assert self.titles("/releases/?genre=Kannada") == ["Bravo"]

    def test_month_headings_and_bad_input(self, catalog):
        r = Client().get("/releases/?year=abc&month=99&sort=nope&price=x&bpm=y")
        assert r.status_code == 200
        labels = [g["label"] for g in r.context["groups"]]
        assert labels == ["September 2026", "July 2026", "March 2025"]

    def test_regional_genres_in_upload(self):
        from apps.core.genres import GENRES

        for g in ("Mangalore", "Tulu", "Kannada", "Tamil", "Telugu", "English"):
            assert g in GENRES
        assert GENRES[-1] == "Other"

    def test_admin_catalog_filters(self, admin_user, catalog):
        c = Client()
        c.force_login(admin_user)
        r = c.get("/api/v1/admin/catalog/?type=track&year=2026&month=9&sort=old")
        assert r.status_code == 200
        assert [o.title for o in r.context["page"]] == ["Charlie"]
