"""Daily Telegram summary for the admin chat (runs with the /cron/weekly-sales/ job, 09:30 IST)."""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Send the admin chat today's numbers and anything waiting."

    def handle(self, *args, **opts):
        from apps.admin_panel import bot

        try:
            bot.daily_summary()
        except Exception as exc:  # never fail the cron job over a chat message
            self.stderr.write(f"Telegram summary skipped: {exc}")
