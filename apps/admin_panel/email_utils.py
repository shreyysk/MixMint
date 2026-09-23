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

    url = "https://api.resend.com/emails"
    headers = {"Authorization": f"Bearer {settings.RESEND_API_KEY}", "Content-Type": "application/json"}
    payload = {"from": settings.FROM_EMAIL, "to": [to_email], "subject": subject, "html": html_content}

    response = requests.post(url, json=payload, headers=headers)
    return response.json()
