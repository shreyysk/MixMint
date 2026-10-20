import logging
import requests
from django.conf import settings

logger = logging.getLogger("mixmint")


def send_email(to_email, subject, html_content):
    """
    Sends an email using the Resend API.
    """
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured. Email to %s not sent: %s", to_email, subject)
        return None

    try:
        from apps.core.email_budget import route

        if not route([to_email], subject, html_content):
            return {"skipped": True}
    except Exception:
        logger.exception("Email budget check failed; sending anyway")
    url = "https://api.resend.com/emails"
    headers = {"Authorization": f"Bearer {settings.RESEND_API_KEY}", "Content-Type": "application/json"}
    payload = {"from": settings.FROM_EMAIL, "to": [to_email], "subject": subject, "html": html_content}

    response = requests.post(url, json=payload, headers=headers, timeout=15)
    if response.ok:
        try:
            from apps.admin_panel.plan_watch import count_email

            count_email()  # this path skips the mail backend, so count here
        except Exception:
            pass
    return response.json()
