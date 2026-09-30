"""Help desk + Telegram bridge, DJ edit/delete + store profile, account settings, DJ re-apply."""

from decimal import Decimal
from unittest import mock

import pytest
from django.test import Client

TG = dict(TELEGRAM_BOT_TOKEN="123:abc", TELEGRAM_ADMIN_CHAT_ID="999", TELEGRAM_BOT_USERNAME="mixmint_bot")


def _login(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def sent():
    """Capture every Telegram sendMessage instead of calling the API."""
    calls = []

    def fake(method, payload):
        calls.append((method, payload))
        return {"message_id": len(calls)}

    with mock.patch("apps.admin_panel.support.tg", side_effect=fake):
        yield calls


def _texts(calls, chat):
    return [p["text"] for m, p in calls if m == "sendMessage" and str(p["chat_id"]) == chat]


@pytest.fixture(autouse=False)
def tg_settings(settings):
    for k, v in TG.items():
        setattr(settings, k, v)


@pytest.mark.django_db
@pytest.mark.usefixtures("tg_settings")
class TestHelpDesk:
    URL = "/api/v1/platform/support/ticket/"

    def test_guest_needs_email_then_admin_is_alerted(self, client, sent, django_capture_on_commit_callbacks):
        assert client.post(self.URL, {"message": "My download failed"}, content_type="application/json").status_code == 400
        with django_capture_on_commit_callbacks(execute=True):
            r = client.post(self.URL, {"message": "My download failed", "email": "g@x.com"}, content_type="application/json")
        assert r.status_code == 201
        from apps.admin_panel.models import SupportTicket

        t = SupportTicket.objects.get()
        assert t.user is None and t.guest_email == "g@x.com" and t.messages.count() == 1
        alert = _texts(sent, "999")[0]
        assert f"#{t.id}" in alert and "Reply to this message" in alert

    def test_honeypot_creates_nothing(self, client, sent):
        client.post(self.URL, {"message": "buy pills now", "email": "b@x.com", "website": "spam"}, content_type="application/json")
        from apps.admin_panel.models import SupportTicket

        assert not SupportTicket.objects.exists()

    def test_user_sees_thread_and_can_reply(self, user, sent):
        c = _login(user)
        tid = c.post(self.URL, {"message": "Where is my invoice?", "category": "order"}, content_type="application/json").json()["id"]
        r = c.post(f"/api/v1/platform/support/tickets/{tid}/reply/", {"message": "Order MM_123"}, content_type="application/json")
        assert [m["body"] for m in r.json()["messages"]] == ["Where is my invoice?", "Order MM_123"]
        assert c.get("/api/v1/platform/support/tickets/").json()[0]["id"] == tid

    def test_webhook_rejects_wrong_secret(self, client):
        r = client.post("/telegram/webhook/", {}, content_type="application/json", HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="nope")
        assert r.status_code == 403

    def _hook(self, client, update):
        from apps.admin_panel.support import webhook_secret

        return client.post("/telegram/webhook/", update, content_type="application/json", HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=webhook_secret())

    def test_telegram_round_trip(self, client, sent, django_capture_on_commit_callbacks):
        from apps.admin_panel.models import SupportTicket

        user_chat = {"id": 555, "username": "priya", "first_name": "Priya"}
        self._hook(client, {"message": {"chat": user_chat, "text": "/start help"}})
        assert "MixMint team" in _texts(sent, "555")[0]
        with django_capture_on_commit_callbacks(execute=True):
            self._hook(client, {"message": {"chat": user_chat, "text": "Payment done but no download"}})
        t = SupportTicket.objects.get()
        assert t.telegram_chat_id == "555" and t.telegram_username == "priya"
        alert = _texts(sent, "999")[-1]
        # admin replies to the alert in Telegram → the customer gets it in their chat
        self._hook(client, {"message": {"chat": {"id": 999}, "text": "Fixed, try again now", "reply_to_message": {"text": alert}}})
        assert "Fixed, try again now" in _texts(sent, "555")[-1]
        t.refresh_from_db()
        assert t.status == "answered" and t.messages.filter(sender="admin").exists()
        self._hook(client, {"message": {"chat": {"id": 999}, "text": f"/close {t.id}"}})
        t.refresh_from_db()
        assert t.status == "closed"

    def test_strangers_cannot_answer_as_admin(self, client, sent):
        from apps.admin_panel.support import open_ticket

        t = open_ticket(body="help me please", email="a@b.com")
        self._hook(client, {"message": {"chat": {"id": 777}, "text": "I'm the admin", "reply_to_message": {"text": f"#{t.id}"}}})
        assert not t.messages.filter(sender="admin").exists()

    def test_admin_web_reply_goes_by_email(self, admin_user, sent):
        from apps.admin_panel.support import open_ticket

        t = open_ticket(body="Question from a guest", email="guest@x.com")
        with mock.patch("apps.admin_panel.email_utils.send_email") as mail:
            _login(admin_user).post(f"/api/v1/admin/support/{t.id}/", {"action": "reply", "body": "Here you go"})
        assert mail.call_args.kwargs["to_email"] == "guest@x.com"
        html = _login(admin_user).get("/api/v1/admin/support/?status=all").content.decode()
        assert f"#{t.id}" in html

    def test_help_button_on_shop_pages_only(self, client, admin_user):
        assert "mm-help-panel" in client.get("/").content.decode()
        assert "t.me/mixmint_bot?start=help" in client.get("/contact/").content.decode()
        assert "mm-help-panel" not in _login(admin_user).get("/api/v1/admin/dashboard/").content.decode()


@pytest.mark.django_db
class TestDJTools:
    def test_edit_hide_and_delete_track(self, dj_user, track):
        c = _login(dj_user[0])
        assert c.get(f"/dashboard/dj/track/{track.id}/edit/").status_code == 200
        r = c.post(f"/dashboard/dj/track/{track.id}/edit/", {
            "title": "New Title", "price": "149", "youtube_url": "https://youtu.be/dQw4w9WgXcQ", "genre": "House",
        })
        assert r.status_code == 302
        track.refresh_from_db()
        assert track.title == "New Title" and track.price == Decimal("149") and not track.is_active
        c.post(f"/dashboard/dj/track/{track.id}/delete/")
        track.refresh_from_db()
        assert track.is_deleted
        assert f"/dashboard/dj/track/{track.id}/edit/" not in c.get("/dashboard/dj/").content.decode()

    def test_other_dj_cannot_edit(self, track, db):
        from apps.accounts.models import DJProfile, User

        other = User.objects.create_user(email="o@x.com", password="Str0ng!Passw0rd")
        other.profile.role = "dj"
        other.profile.save()
        DJProfile.objects.create(profile=other.profile, dj_name="Other", slug="other", status="approved")
        assert _login(other).get(f"/dashboard/dj/track/{track.id}/edit/").status_code == 404
        assert _login(other).post(f"/dashboard/dj/track/{track.id}/delete/").status_code == 404

    def test_album_edit_keeps_minimum_price(self, dj_user, album):
        c = _login(dj_user[0])
        r = c.post(f"/dashboard/dj/album/{album.id}/edit/", {"title": "A", "price": "10", "youtube_url": "https://youtu.be/dQw4w9WgXcQ", "is_active": "on"})
        assert r.status_code == 400 and "at least" in r.content.decode()

    def test_store_profile(self, dj_user, client):
        u, dj = dj_user
        c = _login(u)
        r = c.post("/dashboard/dj/profile/", {"dj_name": "Test DJ", "bio": "Pune techno", "location": "Pune",
                                              "genres": "Techno, House", "instagram": "facebook.com/x"})
        assert r.status_code == 400
        c.post("/dashboard/dj/profile/", {"dj_name": "Test DJ", "bio": "Pune techno", "location": "Pune",
                                          "genres": "Techno, House", "instagram": "instagram.com/testdj"})
        dj.refresh_from_db()
        assert dj.social_links == {"instagram": "https://instagram.com/testdj"} and dj.genres == ["Techno", "House"]
        html = client.get("/dj/test-dj/").content.decode()
        assert "Pune" in html and "https://instagram.com/testdj" in html


@pytest.mark.django_db
class TestAccountSettings:
    def test_name_and_password(self, user):
        c = _login(user)
        assert c.get("/account/").status_code == 200
        c.post("/account/", {"action": "name", "full_name": "Priya R"})
        user.profile.refresh_from_db()
        assert user.profile.full_name == "Priya R"
        c.post("/account/", {"action": "password", "current_password": "wrong", "new_password": "N3w!Passw0rd", "confirm_password": "N3w!Passw0rd"})
        user.refresh_from_db()
        assert user.check_password("StrongPass123!")
        c.post("/account/", {"action": "password", "current_password": "StrongPass123!", "new_password": "N3w!Passw0rd", "confirm_password": "N3w!Passw0rd"})
        user.refresh_from_db()
        assert user.check_password("N3w!Passw0rd")
        assert c.get("/account/").status_code == 200  # still logged in

    def test_close_account(self, user):
        c = _login(user)
        c.post("/account/", {"action": "delete", "confirm": "nope"})
        user.profile.refresh_from_db()
        assert not user.profile.is_banned
        r = c.post("/account/", {"action": "delete", "confirm": "StrongPass123!"})
        user.profile.refresh_from_db()
        assert r.status_code == 302 and user.profile.is_banned
        assert c.get("/account/").status_code == 302  # logged out

    def test_deletion_endpoint_needs_post(self, user):
        assert _login(user).get("/privacy/delete/").status_code == 405


@pytest.mark.django_db
def test_rejected_dj_can_apply_again(user):
    from apps.accounts.models import DJProfile

    DJProfile.objects.create(profile=user.profile, dj_name="X", slug="xdj", status="rejected")
    c = _login(user)
    assert "Apply again" in c.get("/apply-dj/").content.decode()
    c.post("/apply-dj/", {"reapply": "1"})
    assert not DJProfile.objects.filter(profile=user.profile).exists()
    assert c.get("/apply-dj/").status_code == 200
