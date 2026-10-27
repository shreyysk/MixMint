"""Check an email sender works: python manage.py send_test_email you@example.com [--provider smtp|resend]."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.core import mailer


class Command(BaseCommand):
    help = "Send a test email through Resend, the Hostinger SMTP backup, or whichever the site would use."

    def add_arguments(self, parser):
        parser.add_argument("to")
        parser.add_argument("--provider", choices=["auto", "resend", "smtp"], default="auto")

    def handle(self, to, provider, **opts):
        msg = {"from": settings.FROM_EMAIL, "to": [to], "subject": "MixMint test email",
               "html": "<p>This is a test from MixMint. If you can read it, email sending works.</p>"}
        if provider == "auto":
            used = mailer.deliver(msg)
        elif provider == "smtp":
            if not mailer.smtp_ready():
                raise CommandError("Set SMTP_USER and SMTP_PASSWORD first.")
            mailer._send_smtp(msg)
            used = "smtp"
        else:
            if not mailer.resend_ready():
                raise CommandError("Set RESEND_API_KEY first.")
            mailer._send_resend(msg)
            used = "resend"
        if not used:
            raise CommandError("No email provider is configured.")
        self.stdout.write(self.style.SUCCESS(f"Sent to {to} via {used}."))
