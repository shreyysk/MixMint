"""Admin console: every page renders for admins, is closed to everyone else, and the actions work."""

from unittest import mock

import pytest
from django.test import Client

from apps.admin_panel.models import AuditLog, ContentReport, MaintenanceMode

P = "/api/v1/admin/"


@pytest.fixture
def adm(admin_user):
    c = Client()
    c.force_login(admin_user)
    return c


@pytest.fixture
def staff(db):
    from apps.accounts.models import User

    u = User.objects.create_user(email="staff@mixmint.site", password="StaffPass123!")
    u.is_staff = True
    u.save(update_fields=["is_staff"])
    return u


PAGES = ["search/?q=test", "users/", "users/?role=dj&status=frozen&q=x", "orders/", "orders/?status=paid&days=30&type=track",
         "catalog/", "catalog/?type=album", "catalog/?type=bundle&status=removed", "reports/", "reports/?show=all",
         "waitlist/", "messages/", "activity/", "activity/?tab=payments&errors=1", "activity/?tab=fraud", "settings/", "dashboard/"]


@pytest.mark.parametrize("path", PAGES)
def test_pages_render_for_admin(adm, purchase, album, path):
    r = adm.get(P + path)
    assert r.status_code == 200, path
    assert b"Traceback" not in r.content


def test_detail_pages_render(adm, purchase, album, user, dj_user):
    assert adm.get(f"{P}users/{user.pk}/").status_code == 200
    r = adm.get(f"{P}users/{dj_user[0].pk}/")
    assert r.status_code == 200 and b"Give Pro" in r.content
    assert adm.get(f"{P}orders/{purchase.pk}/").status_code == 200
    assert adm.get(f"{P}catalog/track/{purchase.content_id}/").status_code == 200
    assert adm.get(f"{P}catalog/album/{album.pk}/").status_code == 200


def test_closed_to_non_admins(user, purchase):
    anon = Client()
    r = anon.get(P + "users/")
    assert r.status_code == 302 and "/login/" in r["Location"]
    c = Client()
    c.force_login(user)
    for path in ["users/", "orders/", f"orders/{purchase.pk}/", "catalog/", "messages/", "settings/", "export/users.csv"]:
        assert c.get(P + path).status_code == 403, path
    assert c.post(f"{P}users/{user.pk}/", {"action": "make_admin"}).status_code == 403


def test_search_finds_user_order_release(adm, purchase, track):
    r = adm.get(P + "search/", {"q": "buyer@example"})
    assert b"buyer@example.com" in r.content
    r = adm.get(P + "search/", {"q": track.title[:5]})
    assert track.title.encode() in r.content


def test_freeze_ban_and_audit(adm, user):
    url = f"{P}users/{user.pk}/"
    adm.post(url, {"action": "freeze", "reason": "chargeback"})
    user.profile.refresh_from_db()
    assert user.profile.is_frozen
    adm.post(url, {"action": "ban"})
    user.profile.refresh_from_db()
    assert user.profile.is_banned
    adm.post(url, {"action": "unban"})
    adm.post(url, {"action": "unfreeze"})
    user.profile.refresh_from_db()
    assert not user.profile.is_frozen and not user.profile.is_banned
    assert AuditLog.objects.filter(action__icontains="buyer@example.com").count() >= 4


def test_cannot_lock_out_self(adm, admin_user):
    adm.post(f"{P}users/{admin_user.pk}/", {"action": "freeze"})
    admin_user.profile.refresh_from_db()
    assert not admin_user.profile.is_frozen


def test_edit_name_email_and_duplicate(adm, user, second_user):
    url = f"{P}users/{user.pk}/"
    adm.post(url, {"action": "edit", "full_name": "Priya", "email": "priya@example.com"})
    user.refresh_from_db()
    assert user.email == "priya@example.com" and user.profile.full_name == "Priya"
    adm.post(url, {"action": "edit", "full_name": "Priya", "email": second_user.email})
    user.refresh_from_db()
    assert user.email == "priya@example.com"


def test_pro_and_admin_rights(adm, dj_user, user, staff):
    u, _ = dj_user
    adm.post(f"{P}users/{u.pk}/", {"action": "give_pro", "days": "30"})
    u.profile.refresh_from_db()
    assert u.profile.is_pro_dj and u.profile.storage_quota_mb >= 20480
    adm.post(f"{P}users/{u.pk}/", {"action": "end_pro"})
    u.profile.refresh_from_db()
    assert not u.profile.is_pro_dj
    adm.post(f"{P}users/{user.pk}/", {"action": "make_admin"})  # superuser may
    user.refresh_from_db()
    assert user.is_staff
    s = Client()
    s.force_login(staff)  # a plain admin may not hand out admin rights
    s.post(f"{P}users/{user.pk}/", {"action": "revoke_admin"})
    user.refresh_from_db()
    assert user.is_staff


def test_signin_link_and_notify(adm, user):
    with mock.patch("apps.admin_panel.email_utils.send_email") as send:
        adm.post(f"{P}users/{user.pk}/", {"action": "signin_link"})
        adm.post(f"{P}users/{user.pk}/", {"action": "notify", "title": "Hi", "message": "Hello", "also_email": "on"})
    assert send.call_count == 2
    from apps.accounts.models import InAppNotification

    assert InAppNotification.objects.filter(user=user.profile, title="Hi").exists()


def test_order_actions(adm, purchase):
    url = f"{P}orders/{purchase.pk}/"
    purchase.download_completed = True
    purchase.save(update_fields=["download_completed"])
    adm.post(url, {"action": "redownload"})
    purchase.refresh_from_db()
    assert not purchase.download_completed
    adm.post(url, {"action": "revoke"})
    purchase.refresh_from_db()
    assert purchase.is_revoked
    adm.post(url, {"action": "restore"})
    purchase.refresh_from_db()
    assert not purchase.is_revoked
    with mock.patch("apps.commerce.views.execute_refund", return_value=True) as ex:
        adm.post(url, {"action": "refund", "note": "duplicate"})
    assert ex.called


def test_order_recheck_pending(adm, purchase):
    purchase.status, purchase.gateway_order_id, purchase.payment_gateway = "pending", "order_X", "razorpay"
    purchase.save(update_fields=["status", "gateway_order_id", "payment_gateway"])
    with mock.patch("apps.payments.views._fulfil_from_status", return_value="success") as f:
        adm.post(f"{P}orders/{purchase.pk}/", {"action": "recheck"})
    f.assert_called_once_with("order_X", "razorpay")


def test_orders_csv(adm, purchase):
    r = adm.get(P + "export/orders.csv")
    assert r.status_code == 200 and r["Content-Type"].startswith("text/csv")
    assert b"buyer@example.com" in r.content
    for what in ("users", "djs", "payouts", "waitlist"):
        assert adm.get(f"{P}export/{what}.csv").status_code == 200


def test_catalog_hide_edit_remove(adm, track):
    adm.post(P + "catalog/", {"kind": "track", "pk": track.pk, "action": "hide"})
    track.refresh_from_db()
    assert not track.is_active
    url = f"{P}catalog/track/{track.pk}/"
    adm.post(url, {"action": "save", "title": "New name", "price": "149", "description": "x", "is_active": "on"})
    track.refresh_from_db()
    assert track.title == "New name" and int(track.price) == 149 and track.is_active
    adm.post(url, {"action": "save", "title": "New name", "price": "-5"})
    track.refresh_from_db()
    assert int(track.price) == 149
    adm.post(url, {"action": "remove", "reason": "copyright"})
    track.refresh_from_db()
    assert track.is_deleted
    adm.post(url, {"action": "restore"})
    track.refresh_from_db()
    assert not track.is_deleted


def test_report_takedown(adm, track, user):
    r = ContentReport.objects.create(reporter=user.profile, content_type="track", content_id=track.pk, report_type="copyright", reason="Not theirs")
    page = adm.get(P + "reports/")
    assert b"Not theirs" in page.content
    adm.post(P + "reports/", {"src": "content", "id": r.pk, "action": "takedown", "note": "label claim"})
    r.refresh_from_db()
    track.refresh_from_db()
    assert r.status == "resolved" and not track.is_active


def test_messages_broadcast(adm, user, dj_user):
    from apps.accounts.models import InAppNotification

    r = adm.post(P + "messages/", {"audience": "buyers", "title": "Launch", "message": "We're live", "in_app": "on", "confirm": "on"})
    assert r.status_code == 302
    assert InAppNotification.objects.filter(title="Launch", user=user.profile).exists()
    assert not InAppNotification.objects.filter(title="Launch", user=dj_user[0].profile).exists()
    adm.post(P + "messages/", {"audience": "all", "title": "NoConfirm", "message": "x", "in_app": "on"})
    assert not InAppNotification.objects.filter(title="NoConfirm").exists()


def test_waitlist_delete(adm):
    from apps.accounts.models import Waitlist

    w = Waitlist.objects.create(email="w@example.com")
    assert b"w@example.com" in adm.get(P + "waitlist/").content
    adm.post(P + "waitlist/", {"action": "delete", "ids": [w.pk]})
    assert not Waitlist.objects.filter(pk=w.pk).exists()


def test_settings_maintenance(adm):
    adm.post(P + "settings/", {"action": "mode", "mode": "maintenance", "message": "Back soon"})
    assert MaintenanceMode.objects.order_by("-created_at").first().mode == "maintenance"
    adm.post(P + "settings/", {"action": "mode", "mode": "normal"})
    assert MaintenanceMode.objects.order_by("-created_at").first().mode == "normal"
    adm.post(P + "settings/", {"action": "invoices"})
    from apps.admin_panel.models import SystemSetting

    assert SystemSetting.objects.get(key="invoice_generation_enabled").value is False
