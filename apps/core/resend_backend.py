"""Django email backend that sends through the Resend HTTP API (settings.RESEND_API_KEY)."""

import logging

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger("mixmint")


class ResendEmailBackend(BaseEmailBackend):
    api_url = "https://api.resend.com/emails"

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages or []:
            html = None
            for content, mimetype in getattr(message, "alternatives", []) or []:
                if mimetype == "text/html":
                    html = content
            payload = {
                "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
                "to": list(message.to),
                "subject": message.subject,
            }
            if message.cc:
                payload["cc"] = list(message.cc)
            if message.bcc:
                payload["bcc"] = list(message.bcc)
            if message.reply_to:
                payload["reply_to"] = list(message.reply_to)
            if html:
                payload["html"] = html
            if message.body:
                payload["text"] = message.body
            try:
                resp = requests.post(
                    self.api_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                    timeout=15,
                )
                resp.raise_for_status()
                sent += 1
            except Exception:
                logger.exception("Resend email to %s failed", payload["to"])
                if not self.fail_silently:
                    raise
        return sent
