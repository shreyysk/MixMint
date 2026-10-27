"""Run the scheduled MixMint jobs that are due this hour (UTC).

On Railway a small cron service runs `python manage.py cron_tick` once an hour (it starts, runs the due
jobs and exits, so it only costs a few seconds a day). The schedule matches the old vercel.json crons;
the jobs themselves are the same ones /cron/<job>/ runs (apps/core/cron_views.JOBS).

    python manage.py cron_tick            # jobs due now
    python manage.py cron_tick --job cleanup   # one job by name, now
"""

import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger("mixmint")

# job -> (UTC hour, weekday or None for every day). weekday: Monday=0 ... Friday=4
SCHEDULE = {
    "release-escrow": (1, None),
    "payout-cron": (2, None),
    "cleanup": (3, None),
    "weekly-sales": (4, None),  # also sends the daily Telegram summary (09:30 IST)
    "payouts": (5, 4),  # Fridays
}


def due(now):
    return [job for job, (hour, weekday) in SCHEDULE.items()
            if now.hour == hour and (weekday is None or now.weekday() == weekday)]


class Command(BaseCommand):
    help = "Run the MixMint scheduled jobs due this hour (UTC)."

    def add_arguments(self, parser):
        parser.add_argument("--job", help="Run one job now, by name")

    def handle(self, *args, **opts):
        from apps.core.cron_views import JOBS

        jobs = [opts["job"]] if opts.get("job") else due(timezone.now())
        if not jobs:
            self.stdout.write("Nothing due this hour.")
            return
        failed = []
        for job in jobs:
            for cmd in JOBS.get(job, []):
                try:
                    call_command(cmd)
                    self.stdout.write(f"ok {job}: {cmd}")
                except Exception:
                    logger.exception("Cron %s / %s failed", job, cmd)
                    failed.append(f"{job}:{cmd}")
        if failed:
            self.stderr.write("Failed: " + ", ".join(failed))
