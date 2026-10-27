import datetime
from unittest import mock

from django.core.management import call_command

from apps.core.management.commands.cron_tick import due


def t(day, hour):  # 2026-10-26 is a Monday
    return datetime.datetime(2026, 10, 26 + day, hour, 0, tzinfo=datetime.timezone.utc)


def test_schedule_matches_old_vercel_crons():
    assert due(t(0, 1)) == ["release-escrow"]
    assert due(t(0, 4)) == ["weekly-sales"]
    assert due(t(0, 5)) == []
    assert due(t(4, 5)) == ["payouts"]  # Friday
    assert due(t(0, 13)) == []


def test_runs_due_job_commands(db):
    with mock.patch("apps.core.management.commands.cron_tick.call_command") as cc:
        call_command("cron_tick", job="cleanup")
    assert [c.args[0] for c in cc.call_args_list] == ["cleanup_tokens", "telegram_vault", "cleanup_uploads"]
