"""Send one email through the first provider that works: Resend (HTTP API), then SMTP (Hostinger Mail).

Order comes from EMAIL_PROVIDER:
  auto    (default) Resend while it is under its own daily/monthly limit, then SMTP.
  resend  Resend only.            smtp  SMTP only (e.g. when Resend is switched off).
If the first provider fails (error, limit reached, account paused), the next one is tried, so receipts and
sign-in links still go out. Each provider's sends are counted separately (plan_watch) and together (budget).

SMTP note: Railway blocks outbound SMTP on Free/Trial/Hobby plans, so SMTP works on Vercel or Railway Pro.
"""

import logging
from email.utils import formataddr, parseaddr

from django.conf import settings

logger = logging.getLogger("mixmint")


def resend_ready():
    return bool(getattr(settings, "RESEND_API_KEY", ""))


def smtp_ready():
    return bool(getattr(settings, "SMTP_USER", "") and getattr(settings, "SMTP_PASSWORD", ""))


def ready():
    return resend_ready() or smtp_ready()


def provider_limits():
    """{provider: (per day, per month)} for every configured provider."""
    out = {}
    if resend_ready():
        out["resend"] = (int(getattr(settings, "RESEND_DAILY_LIMIT", 100) or 100), int(getattr(settings, "RESEND_MONTHLY_LIMIT", 3000) or 3000))
    if smtp_ready():
        day = int(getattr(settings, "SMTP_DAILY_LIMIT", 100) or 100)
        out["smtp"] = (day, day * 30)
    return out


def order():
    pref = (getattr(settings, "EMAIL_PROVIDER", "auto") or "auto").lower()
    chain = {"resend": ["resend"], "smtp": ["smtp"]}.get(pref, ["resend", "smtp"])
    ready_map = {"resend": resend_ready(), "smtp": smtp_ready()}
    return [p for p in chain if ready_map[p]]


def _under_limit(provider):
    from apps.admin_panel.plan_watch import emails

    lim = provider_limits().get(provider)
    if not lim:
        return False
    day, month = emails(provider)
    return day < lim[0] and month < lim[1]


def _smtp_from(from_email):
    """Hostinger only relays mail sent as the logged-in mailbox, so keep the display name, swap the address."""
    name, addr = parseaddr(from_email or settings.DEFAULT_FROM_EMAIL)
    user = settings.SMTP_USER
    if addr.lower() == user.lower():
        return from_email
    return formataddr((name or "MixMint", user))


def _send_resend(msg):
    from apps.core.resend_backend import post_resend

    payload = {"from": msg["from"], "to": msg["to"], "subject": msg["subject"]}
    for key in ("cc", "bcc", "reply_to", "html", "text"):
        if msg.get(key):
            payload[key] = msg[key]
    post_resend(payload)


def smtp_connection():
    from django.core.mail import get_connection

    port = int(getattr(settings, "SMTP_PORT", 465) or 465)
    return get_connection(
        "django.core.mail.backends.smtp.EmailBackend",
        host=getattr(settings, "SMTP_HOST", "smtp.hostinger.com") or "smtp.hostinger.com",
        port=port, username=settings.SMTP_USER, password=settings.SMTP_PASSWORD,
        use_ssl=port == 465, use_tls=port == 587, timeout=20, fail_silently=False,
    )


def smtp_message(msg, connection=None):
    from django.core.mail import EmailMultiAlternatives

    m = EmailMultiAlternatives(
        subject=msg["subject"], body=msg.get("text") or "", from_email=_smtp_from(msg["from"]),
        to=msg["to"], cc=msg.get("cc") or None, bcc=msg.get("bcc") or None,
        reply_to=msg.get("reply_to") or [parseaddr(msg["from"])[1]], connection=connection,
    )
    if msg.get("html"):
        m.attach_alternative(msg["html"], "text/html")
        if not msg.get("text"):
            from apps.core.email_budget import _plain

            m.body = _plain(msg["html"], "")
    return m


def _send_smtp(msg):
    smtp_message(msg, connection=smtp_connection()).send()


SENDERS = {"resend": _send_resend, "smtp": _send_smtp}


def deliver(msg):
    """msg: {from, to: [..], subject, html?, text?, cc?, bcc?, reply_to?}. Returns the provider used, or None."""
    from apps.admin_panel.plan_watch import count_email

    msg = dict(msg, **{"from": msg.get("from") or settings.DEFAULT_FROM_EMAIL})
    chain = order()
    # Prefer providers with room left today; full ones are still tried last for critical mail.
    chain = sorted(chain, key=lambda p: not _under_limit(p))
    last = None
    for provider in chain:
        try:
            SENDERS[provider](msg)
        except Exception as exc:  # try the next provider
            last = exc
            logger.warning("Email via %s failed (%s): %s", provider, type(exc).__name__, (msg.get("subject") or "")[:60])
            continue
        try:
            count_email(provider)
        except Exception:
            pass
        return provider
    if last is not None:
        logger.error("Email not sent by any provider: %s", (msg.get("subject") or "")[:60])
        raise last
    logger.warning("No email provider configured. Not sent: %s", (msg.get("subject") or "")[:60])
    return None
