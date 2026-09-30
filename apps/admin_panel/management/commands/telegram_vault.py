"""Copy uploads the Telegram vault channels don't have yet (backfill + retries).

    python manage.py telegram_vault            # everything missing, up to 4 minutes
    python manage.py telegram_vault --status   # show what's linked and counts
"""

from django.core.management.base import BaseCommand

from apps.admin_panel import vault


class Command(BaseCommand):
    help = "Archive uploaded tracks/ZIPs to the private Telegram channels."

    def add_arguments(self, parser):
        parser.add_argument("--status", action="store_true")
        parser.add_argument("--budget", type=int, default=240, help="Seconds to spend (default 240).")

    def handle(self, *args, **opts):
        if opts["status"]:
            s = vault.status()
            self.stdout.write(f"singles: {s['singles_title'] or s['singles'] or 'not linked'}")
            self.stdout.write(f"zips:    {s['zips_title'] or s['zips'] or 'not linked'}")
            self.stdout.write(f"link code: {s['code']}   counts: {s['counts']}")
            return
        if not (vault.enabled("track") or vault.enabled("album")):
            self.stdout.write("Vault not linked yet: nothing to do.")
            return
        done = vault.sweep(budget_seconds=opts["budget"])
        self.stdout.write(self.style.SUCCESS(f"Vault sweep: {done}"))
