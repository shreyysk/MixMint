"""Delete abandoned uploads: files a DJ uploaded that no track or album pack uses, older than a day.
Runs in the daily cleanup cron so storage isn't filled with half-finished tries."""

import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger("mixmint")


class Command(BaseCommand):
    help = "Delete R2 uploads that no release references (older than 24 h)."

    def handle(self, *args, **opts):
        from apps.accounts.models import DJProfile
        from apps.core import r2

        if not r2.configured():
            self.stdout.write("R2 not configured; skipped.")
            return
        total = 0
        for dj in DJProfile.objects.all().only("id"):
            for kind in ("audio", "album"):
                try:
                    total += r2.delete_orphans(kind, dj)
                except Exception:
                    logger.exception("Upload cleanup failed for DJ %s (%s)", dj.id, kind)
        self.stdout.write(f"Deleted {total} abandoned upload(s).")
