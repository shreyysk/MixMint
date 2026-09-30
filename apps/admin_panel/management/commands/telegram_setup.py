"""Connect the Telegram bot to this site: python manage.py telegram_setup https://mixmint.site"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.admin_panel import support


class Command(BaseCommand):
    help = "Register the Telegram webhook so customers can chat with the bot and admins can reply from Telegram."

    def add_arguments(self, parser):
        parser.add_argument("base_url", nargs="?", default="")

    def handle(self, *args, **opts):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError("TELEGRAM_BOT_TOKEN is not set.")
        base = opts["base_url"] or getattr(settings, "BASE_URL", "")
        if not base.startswith("https://"):
            raise CommandError("Give the public https address, e.g. https://mixmint.site")
        ok, url = support.set_webhook(base)
        if not ok:
            raise CommandError("Telegram refused the webhook. Check the bot token.")
        self.stdout.write(self.style.SUCCESS(f"Connected: Telegram now sends messages to {url}"))
        info = support.webhook_info()
        if info.get("last_error_message"):
            self.stdout.write(f"Last error Telegram saw: {info['last_error_message']}")
