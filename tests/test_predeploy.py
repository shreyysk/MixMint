import pytest
from django.core.management import call_command

from apps.accounts.models import User


@pytest.mark.django_db
def test_predeploy_creates_admin_once(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "Boss@MixMint.site")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "Str0ng!Pass-123")
    call_command("predeploy")
    u = User.objects.get(email="boss@mixmint.site")
    assert u.is_superuser and u.is_staff and u.check_password("Str0ng!Pass-123") and u.profile.role == "admin"
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "changed")
    call_command("predeploy")
    u.refresh_from_db()
    assert u.check_password("Str0ng!Pass-123")


@pytest.mark.django_db
def test_predeploy_without_vars(monkeypatch):
    monkeypatch.delenv("DJANGO_SUPERUSER_EMAIL", raising=False)
    monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)
    call_command("predeploy")
    assert not User.objects.filter(is_superuser=True).exists()
