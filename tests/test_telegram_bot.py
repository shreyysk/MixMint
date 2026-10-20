"""MixMint Telegram bot: linking, buyer/DJ/admin commands, buttons, notifications."""

import time
from decimal import Decimal
from unittest import mock

import pytest

from apps.admin_panel import bot
from apps.admin_panel.models import TelegramLink
from apps.admin_panel.support import handle_update

ADMIN = "999"


@pytest.fixture
def tg(settings):
    settings.TELEGRAM_BOT_TOKEN = "123:abc"
    settings.TELEGRAM_ADMIN_CHAT_ID = ADMIN
    settings.TELEGRAM_BOT_USERNAME = "mixmint_bot"
    calls = []

    def fake(method, payload):
        calls.append((method, payload))
        return {"message_id": len(calls)}

    with mock.patch("apps.admin_panel.support.tg", side_effect=fake):
        yield calls


def texts(calls, chat):
    return [p.get("text", "") or p.get("caption", "") for m, p in calls if m in ("sendMessage", "sendPhoto") and str(p["chat_id"]) == str(chat)]


def buttons(calls, chat):
    out = []
    for m, p in calls:
        if m == "sendMessage" and str(p["chat_id"]) == str(chat):
            for row in (p.get("reply_markup") or {}).get("inline_keyboard", []):
                out += row
    return out


def msg(chat, text, **chat_extra):
    return {"message": {"chat": {"id": chat, **chat_extra}, "text": text}}


def tap(chat, data):
    return {"callback_query": {"id": "cq1", "data": data, "message": {"chat": {"id": chat}}}}


# ─────────────────────────────── linking ───────────────────────────────
@pytest.mark.django_db
def test_link_payload_fits_and_links(tg, user):
    payload = bot.link_payload(user.profile)
    assert payload.startswith("ln_") and len(payload) <= 64
    handle_update(msg(4242, f"/start {payload}", username="priya"))
    link = TelegramLink.objects.get(profile=user.profile)
    assert link.chat_id == "4242" and link.username == "priya"
    assert "Connected" in texts(tg, 4242)[0]


@pytest.mark.django_db
def test_link_expires_and_rejects_tampering(tg, user):
    payload = bot.link_payload(user.profile)
    with mock.patch("apps.admin_panel.bot.time.time", return_value=time.time() + bot.LINK_TTL + 5):
        handle_update(msg(1, f"/start {payload}"))
    handle_update(msg(2, f"/start {payload[:-1]}{'0' if payload[-1] != '0' else '1'}"))
    handle_update(msg(3, "/start dl_" + "0" * 32 + "_abcdef0123456789"))
    assert not TelegramLink.objects.exists()
    assert all("link" in t.lower() for t in texts(tg, 1) + texts(tg, 2) + texts(tg, 3))


@pytest.mark.django_db
def test_one_chat_one_account(tg, user, second_user):
    handle_update(msg(77, f"/start {bot.link_payload(user.profile)}"))
    handle_update(msg(77, f"/start {bot.link_payload(second_user.profile)}"))
    assert list(TelegramLink.objects.values_list("profile_id", flat=True)) == [second_user.profile.pk]
    handle_update(msg(77, "/unlink"))
    assert not TelegramLink.objects.exists()


@pytest.mark.django_db
def test_connect_button_redirects_to_fresh_link(tg, client, user):
    client.force_login(user)
    html = client.get("/account/").content.decode()
    assert "Connect Telegram" in html
    r = client.get("/account/telegram/")
    assert r.status_code == 302 and r["Location"].startswith("https://t.me/mixmint_bot?start=ln_")
    TelegramLink.objects.create(profile=user.profile, chat_id="5", username="me")
    assert "Connected as @me" in client.get("/account/").content.decode()
    client.post("/account/", {"action": "telegram_unlink"})
    assert not TelegramLink.objects.exists()


@pytest.mark.django_db
def test_connect_card_hidden_without_bot(client, user, settings):
    settings.TELEGRAM_BOT_TOKEN = ""
    client.force_login(user)
    assert "Connect Telegram" not in client.get("/account/").content.decode()


# ─────────────────────────────── commands ───────────────────────────────
@pytest.mark.django_db
def test_start_menu_and_help_desk_greeting(tg):
    handle_update(msg(10, "/start"))
    assert "What would you like to do" in texts(tg, 10)[-1]
    assert any(b.get("callback_data") == "link" for b in buttons(tg, 10))
    handle_update(msg(11, "/start help"))
    assert "MixMint team" in texts(tg, 11)[-1]


@pytest.mark.django_db
def test_new_and_search(tg, track):
    handle_update(msg(10, "/new"))
    assert track.title in texts(tg, 10)[-1]
    handle_update(msg(10, f"/search {track.title[:4]}"))
    assert any(f"/tracks/{track.id}/" in b.get("url", "") for b in buttons(tg, 10))
    handle_update(msg(10, "/search zzzznothing"))
    assert "Nothing found" in texts(tg, 10)[-1]


@pytest.mark.django_db
def test_library_needs_link_then_lists(tg, user, purchase, track):
    handle_update(msg(20, "/library"))
    assert "Connect this chat" in texts(tg, 20)[-1]
    TelegramLink.objects.create(profile=user.profile, chat_id="20")
    handle_update(msg(20, "/library"))
    assert track.title in texts(tg, 20)[-1]


@pytest.mark.django_db
def test_dj_sales_and_balance(tg, dj_user, purchase):
    from apps.commerce.models import DJWallet

    u, dj = dj_user
    DJWallet.objects.update_or_create(dj=dj, defaults={"available_for_payout": Decimal("640"), "total_earnings": Decimal("900")})
    TelegramLink.objects.create(profile=u.profile, chat_id="30")
    handle_update(msg(30, "/sales"))
    assert "Today: 1 sale" in texts(tg, 30)[-1] and "₹85" in texts(tg, 30)[-1]
    handle_update(tap(30, "balance"))
    assert "Ready to receive: ₹640" in texts(tg, 30)[-1]
    assert ("answerCallbackQuery", {"callback_query_id": "cq1"}) in tg


@pytest.mark.django_db
def test_buyer_cannot_use_dj_or_admin_commands(tg, user):
    TelegramLink.objects.create(profile=user.profile, chat_id="40")
    handle_update(msg(40, "/sales"))
    assert "for DJs" in texts(tg, 40)[-1]
    handle_update(msg(40, "/stats"))
    handle_update(msg(40, "/maintenance on"))
    handle_update(tap(40, "paygo:1"))
    from apps.admin_panel.models import MaintenanceMode

    assert not MaintenanceMode.objects.filter(mode="maintenance").exists()
    assert all("Orders" not in t for t in texts(tg, 40))


# ─────────────────────────────── admin ───────────────────────────────
@pytest.mark.django_db
def test_admin_stats_pending_maintenance(tg, purchase):
    handle_update(msg(ADMIN, "/stats"))
    assert "Orders: 1" in texts(tg, ADMIN)[-1]
    handle_update(msg(ADMIN, "/maintenance on"))
    from apps.admin_panel.models import MaintenanceMode

    assert MaintenanceMode.objects.order_by("-id").first().mode == "maintenance"
    handle_update(msg(ADMIN, "/maintenance off"))
    assert MaintenanceMode.objects.order_by("-id").first().mode == "normal"
    handle_update(msg(ADMIN, "/pending"))
    assert texts(tg, ADMIN)[-1] == "Nothing waiting."


@pytest.mark.django_db
def test_admin_payout_button_needs_confirm(tg, dj_user):
    from apps.commerce.models import Payout

    _, dj = dj_user
    p = Payout.objects.create(dj=dj, amount=Decimal("500"), status="pending", hold_reason="Waiting for admin approval: first payout")
    handle_update(msg(ADMIN, "/pending"))
    assert any(b.get("callback_data") == f"pay:{p.id}" for b in buttons(tg, ADMIN))
    with mock.patch("apps.commerce.payout_gateway.dispatch") as dispatch:
        handle_update(tap(ADMIN, f"pay:{p.id}"))
        dispatch.assert_not_called()  # first tap only asks
        assert any(b.get("callback_data") == f"paygo:{p.id}" for b in buttons(tg, ADMIN))
        with mock.patch("apps.commerce.payout_gateway.active_provider", return_value=object()):
            dispatch.return_value = "processing"
            handle_update(tap(ADMIN, f"paygo:{p.id}"))
        dispatch.assert_called_once_with(p.id, approved_by="telegram-admin")
    assert "waiting for the bank" in texts(tg, ADMIN)[-1]


@pytest.mark.django_db
def test_admin_help_desk_commands_still_work(tg):
    from apps.admin_panel.support import open_ticket

    t = open_ticket(body="help", email="a@b.com")
    handle_update(msg(ADMIN, "/open"))
    assert f"#{t.id}" in texts(tg, ADMIN)[-1]
    handle_update(msg(ADMIN, f"/close {t.id}"))
    t.refresh_from_db()
    assert t.status == "closed"


@pytest.mark.django_db
def test_daily_summary(tg, purchase):
    bot.daily_summary()
    assert texts(tg, ADMIN)[-1].startswith("Yesterday")


# ─────────────────────────────── notifications ───────────────────────────────
@pytest.mark.django_db
def test_sale_notifies_dj_by_telegram_and_daily_email(tg, dj_user, user, track, django_capture_on_commit_callbacks):
    from django.utils import timezone

    from apps.commerce.models import Purchase
    from apps.commerce.services import MonetizationService

    u, dj = dj_user
    TelegramLink.objects.create(profile=u.profile, chat_id="50")
    p = Purchase.objects.create(user=user.profile, content_id=track.id, content_type="track", original_price=track.price,
                                price_paid=track.price, seller=dj, status="paid", paid_at=timezone.now())
    with mock.patch("apps.core.email_service.EmailService.send_notice") as mail, django_capture_on_commit_callbacks(execute=True):
        MonetizationService.complete_purchase(p)
    assert f"New sale: {track.title}" in texts(tg, 50)[-1]
    assert not mail.called  # no email per sale
    today = timezone.localdate()
    with mock.patch("apps.core.email_service.EmailService.send_notice", return_value=True) as mail:
        assert bot.sales_digest(today) == 0  # linked to Telegram: no email at all
        TelegramLink.objects.all().delete()
        Purchase.objects.create(user=user.profile, content_id=track.id, content_type="track", original_price=track.price,
                                price_paid=track.price, seller=dj, status="paid", paid_at=timezone.now())
        assert bot.sales_digest(today) == 1
    assert mail.call_count == 1 and mail.call_args.args[0] == "dj@example.com" and "2 sales" in mail.call_args.args[1]


@pytest.mark.django_db
def test_payout_paid_dm(tg, dj_user):
    from apps.commerce.models import Payout

    u, dj = dj_user
    TelegramLink.objects.create(profile=u.profile, chat_id="60")
    p = Payout.objects.create(dj=dj, amount=Decimal("700"), status="completed", utr="UTR123")
    bot.notify_payout(p, True)
    assert "Payout sent: ₹700 (UTR UTR123)" in texts(tg, 60)[-1]


@pytest.mark.django_db
def test_release_posts_to_channel(tg, settings, track):
    settings.TELEGRAM_CHANNEL_ID = "@mixmint_releases"
    track.cover_url = "https://cdn.example.com/c.jpg"
    bot.post_release(track, "track")
    m, p = [c for c in tg if c[0] == "sendPhoto"][-1]
    assert p["chat_id"] == "@mixmint_releases" and track.title in p["caption"]
    assert f"/tracks/{track.id}/" in p["reply_markup"]["inline_keyboard"][0][0]["url"]


@pytest.mark.django_db
def test_notifications_never_raise_without_bot(settings, dj_user):
    from apps.commerce.models import Payout

    settings.TELEGRAM_BOT_TOKEN = ""
    _, dj = dj_user
    bot.notify_payout(Payout.objects.create(dj=dj, amount=Decimal("1"), status="failed"), False)


@pytest.mark.django_db
def test_setup_registers_callbacks_and_commands(tg):
    ok, url = bot.setup("https://mixmint.site")
    hook = [p for m, p in tg if m == "setWebhook"][0]
    assert "callback_query" in hook["allowed_updates"] and url.endswith("/telegram/webhook/")
    scopes = [p.get("scope") for m, p in tg if m == "setMyCommands"]
    assert None in scopes and {"type": "chat", "chat_id": ADMIN} in scopes
