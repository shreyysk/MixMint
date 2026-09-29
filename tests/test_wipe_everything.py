from unittest import mock

import pytest
from django.core.management import CommandError, call_command


@pytest.mark.django_db
def test_refuses_without_confirmation(user):
    with pytest.raises(CommandError):
        call_command("wipe_everything", "--database")
    from apps.accounts.models import User

    assert User.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_wipes_database_storage_and_creates_admin(user, track):
    from apps.accounts.models import User
    from apps.tracks.models import Track

    with mock.patch("boto3.client") as factory, mock.patch(
        "apps.core.management.commands.wipe_everything.getpass.getpass", return_value="Adm1n!Passw0rd"
    ):
        s3 = factory.return_value
        s3.get_paginator.return_value.paginate.return_value = [{"Contents": [{"Key": "a.mp3"}, {"Key": "b.zip"}]}]
        call_command(
            "wipe_everything", "--database", "--storage", "--confirm", "DELETE-EVERYTHING",
            "--admin-email", "Boss@Example.com", "--yes", "--no-backup",
        )
    assert Track.objects.count() == 0
    assert list(User.objects.values_list("email", "is_superuser")) == [("boss@example.com", True)]
    assert User.objects.get().profile.role == "admin"
    assert s3.delete_objects.called
