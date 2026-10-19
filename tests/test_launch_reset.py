"""Admin → Settings → Launch: clear test data."""

from decimal import Decimal

import pytest
from django.test import Client


def _admin(admin_user):
    c = Client()
    c.force_login(admin_user)
    return c


@pytest.mark.django_db
def test_reset_sales_needs_confirm_then_clears_money_keeps_music(admin_user, purchase, track, dj_user):
    from apps.commerce.models import DJWallet, Payout, Purchase

    _, dj = dj_user
    DJWallet.objects.update_or_create(dj=dj, defaults={"total_earnings": Decimal("85"), "available_for_payout": Decimal("85")})
    Payout.objects.create(dj=dj, amount=Decimal("85"), status="completed")
    track.download_count = 9
    track.save(update_fields=["download_count"])
    c = _admin(admin_user)
    html = c.get("/api/v1/admin/settings/").content.decode()
    assert "Launch: clear test data" in html and "1 order" in html
    c.post("/api/v1/admin/settings/", {"action": "launch_reset_sales", "confirm": "reset"})
    assert Purchase.objects.exists()
    c.post("/api/v1/admin/settings/", {"action": "launch_reset_sales", "confirm": "RESET"})
    assert not Purchase.objects.exists() and not Payout.objects.exists()
    assert DJWallet.objects.get(dj=dj).available_for_payout == 0
    track.refresh_from_db()
    assert track.download_count == 0 and not track.is_deleted


@pytest.mark.django_db
def test_delete_accounts_never_deletes_admins(admin_user, user, dj_user):
    from apps.accounts.models import User
    from apps.admin_panel import launch_reset

    u, _ = dj_user
    rows = {r["email"]: r for r in launch_reset.suspects()}
    assert admin_user.email not in rows and rows[user.email]["test"] is True  # example.com
    c = _admin(admin_user)
    c.post("/api/v1/admin/settings/", {"action": "launch_delete_accounts", "confirm": "RESET", "ids": [str(user.pk), str(admin_user.pk)]})
    assert not User.objects.filter(pk=user.pk).exists()
    assert User.objects.filter(pk=admin_user.pk).exists() and User.objects.filter(pk=u.pk).exists()


@pytest.mark.django_db
def test_reset_is_admin_only(user):
    c = Client()
    c.force_login(user)
    r = c.post("/api/v1/admin/settings/", {"action": "launch_reset_sales", "confirm": "RESET"})
    assert r.status_code in (302, 403, 404)
