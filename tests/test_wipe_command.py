from unittest import mock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.django_db
def test_wipe_requires_confirmation(user):
    with pytest.raises(CommandError):
        call_command("wipe_everything", "--database")
    from apps.accounts.models import User

    assert User.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_wipe_database_backs_up_and_empties(user, track, tmp_path, monkeypatch):
    from apps.accounts.models import User
    from apps.tracks.models import Track

    monkeypatch.chdir(tmp_path)
    call_command("wipe_everything", "--database", "--confirm", "DELETE-EVERYTHING", "--yes")
    assert not User.objects.exists() and not Track.objects.exists()
    backups = list(tmp_path.glob("mixmint-backup-*.json"))
    assert backups and backups[0].stat().st_size > 100


@pytest.mark.django_db
def test_wipe_can_be_cancelled(user):
    from apps.accounts.models import User

    with mock.patch("builtins.input", return_value="no"), pytest.raises(CommandError):
        call_command("wipe_everything", "--database", "--confirm", "DELETE-EVERYTHING", "--no-backup")
    assert User.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_users_mode_keeps_admins_and_files(user, track, dj_user, tmp_path, monkeypatch):
    from apps.accounts.models import User
    from apps.tracks.models import Track

    monkeypatch.chdir(tmp_path)
    admin = User.objects.create_superuser(email="boss@example.com", password="Adm1n!Passw0rd")
    with mock.patch("boto3.client") as s3:
        call_command("wipe_everything", "--users", "--confirm", "DELETE-EVERYTHING", "--yes")
    assert not s3.called  # R2 files untouched
    assert list(User.objects.values_list("email", flat=True)) == ["boss@example.com"]
    assert not Track.objects.exists()  # listings belonged to the deleted DJ
    admin.refresh_from_db()
    assert admin.check_password("Adm1n!Passw0rd")
    assert list(tmp_path.glob("mixmint-backup-*.json"))


@pytest.mark.django_db
def test_users_mode_needs_an_admin(user):
    with pytest.raises(CommandError):
        call_command("wipe_everything", "--users", "--confirm", "DELETE-EVERYTHING", "--yes", "--no-backup")
