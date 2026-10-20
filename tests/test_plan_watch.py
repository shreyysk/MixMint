"""Upgrade reminders: when to leave each free plan."""

import pytest

from apps.admin_panel import plan_watch


def levels():
    return {r["key"]: r["level"] for r in plan_watch.status()}


@pytest.mark.django_db
def test_all_fine_on_test_keys(settings):
    settings.CASHFREE_PG_ENV = "sandbox"
    assert set(levels().values()) == {"ok"}
    assert plan_watch.telegram_lines() == ""


@pytest.mark.django_db
def test_live_payments_flag_vercel(settings, purchase):
    settings.CASHFREE_PG_ENV = "production"
    assert levels()["vercel"] == "now"
    assert "Vercel Pro, $20/month" in plan_watch.telegram_lines()


@pytest.mark.django_db
def test_email_counter_flags_resend(settings):
    settings.CASHFREE_PG_ENV = "sandbox"
    for _ in range(85):
        plan_watch.count_email()
    assert plan_watch.emails() == (85, 85)
    assert levels()["resend"] == "now"


@pytest.mark.django_db
def test_settings_page_shows_plans(admin_user, client):
    client.force_login(admin_user)
    html = client.get("/api/v1/admin/settings/").content.decode()
    assert "Plans and costs" in html and "Supabase Pro" in html
