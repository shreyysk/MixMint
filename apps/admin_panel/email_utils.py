import logging
from django.conf import settings

logger = logging.getLogger("mixmint")


def send_email(to_email, subject, html_content):
    """Send one HTML email: Resend first, Hostinger SMTP as backup (see apps.core.mailer)."""
    from apps.core import mailer

    if not mailer.ready():
        logger.warning("No email provider configured. Email to %s not sent: %s", to_email, subject)
        return None
    try:
        from apps.core.email_budget import route

        if not route([to_email], subject, html_content):
            return {"skipped": True}
    except Exception:
        logger.exception("Email budget check failed; sending anyway")
    provider = mailer.deliver({"from": settings.FROM_EMAIL, "to": [to_email], "subject": subject, "html": html_content})
    return {"provider": provider}
