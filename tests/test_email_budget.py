"""Resend quota: Telegram first, dedupe, budget tiers, one receipt per order."""

from unittest import mock

import pytest
from django.core import mail
from django.core.cache import cache

from apps.core import email_budget as eb


@pytest.fixture(autouse=True)
def clean(settings):
    cache.clear()
    settings.TELEGRAM_BOT_TOKEN = "1:a"
    settings.TELEGRAM_ADMIN_CHAT_ID = "999"
    settings.ADMIN_ALERT_EMAIL = "boss@mixmint.site"
    yield
    cache.clear()


def test_kinds():
    assert eb.kind_of("a@b.c", "Your sign-in link") == "critical"
    assert eb.kind_of("a@b.c", "🎵 Your purchase: Song") == "critical"
    assert eb.kind_of("a@b.c", "Welcome to MixMint! 🎧 Let's get started") == "low"
    assert eb.kind_of("a@b.c", "Welcome to MixMint! 🎧 Your DJ account is approved") == "normal"
    assert eb.kind_of("boss@mixmint.site", "⚠️ Transaction Alert") == "admin"


@pytest.mark.django_db
def test_linked_telegram_gets_it_instead(user):
    from apps.admin_panel.models import TelegramLink

    TelegramLink.objects.create(profile=user.profile, chat_id="77")
    with mock.patch("apps.admin_panel.support.tg", return_value={"message_id": 1}) as tg:
        assert eb.route([user.email], "MixMint DJ Application Update", "<p>Hello <a href='https://x.y'>open</a></p>") is False
        assert "open: https://x.y" in tg.call_args.args[1]["text"]
        assert eb.route([user.email], "Payout of ₹500 on its way") is False  # bot already sent it: not forwarded
        assert tg.call_count == 1
        assert eb.route([user.email], "Your sign-in link") is True  # critical stays email
    assert eb.saved() == 2


@pytest.mark.django_db
def test_admin_alerts_go_to_telegram_and_duplicates_drop():
    with mock.patch("apps.admin_panel.support.tg", return_value={"message_id": 1}):
        assert eb.route(["boss@mixmint.site"], "New report") is False
    assert eb.route(["x@y.z"], "Something happened") is True
    assert eb.route(["x@y.z"], "Something happened") is False  # same person+subject within 15 min


@pytest.mark.django_db
def test_budget_tiers(settings):
    settings.RESEND_DAILY_LIMIT = 100
    with mock.patch("apps.admin_panel.plan_watch.emails", return_value=(60, 600)):
        assert eb.route(["a@b.c"], "Welcome to MixMint") is False  # low stops at 50/day
        assert eb.route(["a@b.c"], "Your content was removed") is True
    with mock.patch("apps.admin_panel.plan_watch.emails", return_value=(90, 900)):
        assert eb.route(["c@b.c"], "Your content was removed") is False  # normal stops at 85/day
        assert eb.route(["c@b.c"], "Your sign-in link") is True
    with mock.patch("apps.admin_panel.plan_watch.emails", return_value=(100, 900)):
        assert eb.route(["c@b.c"], "Your sign-in link") is False  # hard cap


@pytest.mark.django_db
def test_backend_respects_route(settings):
    settings.EMAIL_BACKEND = "apps.core.resend_backend.ResendEmailBackend"
    settings.RESEND_API_KEY = "k"
    with mock.patch("apps.core.resend_backend.requests.post") as post, \
         mock.patch("apps.core.email_budget.route", return_value=False):
        from django.core.mail import send_mail

        send_mail("Hi", "x", "a@mixmint.site", ["b@c.d"])
    assert not post.called


@pytest.mark.django_db
def test_one_receipt_per_cart(user, track, settings):
    from decimal import Decimal

    from apps.commerce.models import Purchase
    from apps.core.email_service import EmailService
    from apps.tracks.models import Track

    t2 = Track.objects.create(dj=track.dj, title="Second", price=Decimal("50"), file_key="tracks/x.wav",
                              preview_type="youtube", youtube_url="https://youtube.com/watch?v=abc")
    ps = [Purchase.objects.create(user=user.profile, content_id=t.id, content_type="track", original_price=t.price,
                                  price_paid=t.price, seller=t.dj, status="paid") for t in (track, t2)]
    with mock.patch.object(EmailService, "send_notice", return_value=True) as notice:
        EmailService.send_order_receipt(ps)
    assert notice.call_count == 1 and "2 items" in notice.call_args.args[1]
