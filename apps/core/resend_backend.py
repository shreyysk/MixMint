"""Django email backend for MixMint: budget check, then Resend (HTTP API) with SMTP (Hostinger Mail) as backup.

The provider order and fallback live in apps.core.mailer. This module keeps the Resend HTTP call
(post_resend) and the backend class Django uses for all mail (password reset, EmailService, receipts).
"""

import logging

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger("mixmint")
RESEND_URL = "https://api.resend.com/emails"


def post_resend(payload):
    """Send one email through Resend. Raises on any non-2xx (limit reached, paused account, bad key)."""
    resp = requests.post(RESEND_URL, json=payload, headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"}, timeout=15)
    resp.raise_for_status()
    return resp


class ResendEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        from apps.core import mailer

        sent = 0
        for message in email_messages or []:
            html = None
            for content, mimetype in getattr(message, "alternatives", []) or []:
                if mimetype == "text/html":
                    html = content
            msg = {
                "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
                "to": list(message.to),
                "subject": message.subject,
                "cc": list(message.cc or []),
                "bcc": list(message.bcc or []),
                "reply_to": list(message.reply_to or []),
                "html": html,
                "text": message.body or "",
            }
            try:
                from apps.core.email_budget import route

                if not route(msg["to"], msg["subject"], html or "", message.body or ""):
                    continue
            except Exception:
                logger.exception("Email budget check failed; sending anyway")
            try:
                if mailer.deliver(msg):
                    sent += 1
            except Exception:
                logger.exception("Email to %s failed on every provider", msg["to"])
                if not self.fail_silently:
                    raise
        return sent


MailBackend = ResendEmailBackend
