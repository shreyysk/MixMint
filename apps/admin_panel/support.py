"""
Help desk: people reach the MixMint admin from the site's Help button, the contact page or
the Telegram bot, and the admin answers from Telegram (reply to the alert) or from
Admin → Support. Answers go back the way the question came: Telegram chat or email.

Telegram setup (once): Admin → Support → "Connect Telegram bot" (or `manage.py telegram_setup`)
registers https://<site>/telegram/webhook/ with a secret header.
"""

import hashlib
import logging
import re

import requests
from django.conf import settings
from django.db import transaction
from django.utils.html import escape

logger = logging.getLogger("mixmint")
TICKET_REF = re.compile(r"#(\d{1,9})\b")


# ─────────────────────────────── Telegram plumbing ───────────────────────────────
def _token():
    return getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""


def admin_chat_id():
    return str(getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", "") or "")


def webhook_secret():
    """Secret Telegram echoes in X-Telegram-Bot-Api-Secret-Token (derived, so no extra env var)."""
    explicit = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "") or ""
    return explicit or hashlib.sha256(f"tg-webhook:{settings.SECRET_KEY}".encode()).hexdigest()[:48]


def tg(method, payload):
    """Call the Bot API. Never raises; returns the decoded result or None."""
    if not _token():
        return None
    try:
        r = requests.post(f"https://api.telegram.org/bot{_token()}/{method}", json=payload, timeout=10)
        data = r.json()
        return data.get("result") if data.get("ok") else None
    except Exception as exc:  # the URL holds the token: never log the exception text
        logger.error("Telegram %s failed (%s).", method, type(exc).__name__)
        return None


def tg_send(chat_id, text):
    if not chat_id:
        return None
    return tg("sendMessage", {"chat_id": chat_id, "text": text[:3900], "disable_web_page_preview": True})


def set_webhook(base_url):
    url = base_url.rstrip("/") + "/telegram/webhook/"
    ok = tg("setWebhook", {"url": url, "secret_token": webhook_secret(), "allowed_updates": ["message", "channel_post", "my_chat_member"]})
    tg("setMyCommands", {"commands": [{"command": "start", "description": "Talk to the MixMint team"}]})
    return ok is not None, url


def webhook_info():
    return tg("getWebhookInfo", {}) or {}


# ─────────────────────────────── Tickets ───────────────────────────────
def _alert(ticket, text, first=False):
    from .models import SupportTicket  # noqa: F401

    head = "🆘 New question" if first else "💬 New message"
    site = (getattr(settings, "BASE_URL", "") or "").rstrip("/")
    tg_send(
        admin_chat_id(),
        f"{head} #{ticket.id} [{ticket.category}]\n"
        f"From: {ticket.contact_label()}{' · ' + ticket.contact_email() if ticket.contact_email() else ''}\n"
        f"Subject: {ticket.subject}\n\n{text[:1500]}\n\n"
        f"↩ Reply to this message to answer. /close {ticket.id} to close.\n{site}/api/v1/admin/support/{ticket.id}/",
    )


@transaction.atomic
def open_ticket(*, body, subject="", category="other", priority="medium", user=None, email="", name="",
                chat_id="", tg_username="", via="web"):
    from .models import SupportMessage, SupportTicket

    body = (body or "").strip()[:5000]
    subject = (subject or body.split("\n", 1)[0])[:120] or "Question"
    ticket = SupportTicket.objects.create(
        user=user, guest_email=(email or "")[:254], guest_name=(name or "")[:120], telegram_chat_id=str(chat_id or ""),
        telegram_username=(tg_username or "")[:64], subject=subject, category=category, priority=priority,
        description=body,
    )
    SupportMessage.objects.create(ticket=ticket, sender="user", body=body, via=via)
    transaction.on_commit(lambda: _alert(ticket, body, first=True))
    return ticket


def add_user_message(ticket, body, via="web"):
    from .models import SupportMessage

    body = (body or "").strip()[:5000]
    SupportMessage.objects.create(ticket=ticket, sender="user", body=body, via=via)
    if ticket.status in ("resolved", "closed"):
        ticket.status = "open"
    ticket.save(update_fields=["status", "updated_at"])
    _alert(ticket, body)


def admin_reply(ticket, body, via="web"):
    """Store the admin's answer and deliver it. Returns where it went ('telegram', 'email' or '')."""
    from .models import SupportMessage

    body = (body or "").strip()[:5000]
    SupportMessage.objects.create(ticket=ticket, sender="admin", body=body, via=via)
    ticket.status = "answered"
    ticket.save(update_fields=["status", "updated_at"])

    if ticket.telegram_chat_id and tg_send(ticket.telegram_chat_id, f"MixMint team:\n{body}"):
        return "telegram"
    email = ticket.contact_email()
    if email:
        try:
            from .email_utils import send_email

            site = (getattr(settings, "BASE_URL", "") or "https://mixmint.site").rstrip("/")
            send_email(
                to_email=email,
                subject=f"Re: {ticket.subject} [MixMint #{ticket.id}]",
                html_content=(
                    f"<p>{escape(body).replace(chr(10), '<br>')}</p><hr>"
                    f"<p style='color:#666;font-size:13px'>You asked: {escape(ticket.description[:500])}</p>"
                    f"<p style='font-size:13px'>Reply from the Help button on <a href='{site}'>MixMint</a>"
                    f" (ticket #{ticket.id}).</p>"
                ),
            )
            return "email"
        except Exception:
            logger.exception("Support reply email failed for ticket %s", ticket.id)
    return ""


# ─────────────────────────────── Webhook updates ───────────────────────────────
WELCOME = (
    "Hi! You're talking to the MixMint team 👋\n\n"
    "Type your question here (order ID or track name helps) and we'll reply in this chat, "
    "usually within a few hours."
)


def handle_update(update):
    from . import vault
    from .models import SupportTicket

    if vault.handle_channel_update(update):
        return
    msg = update.get("message") or {}
    chat = msg.get("chat") or {}
    chat_id = str(chat.get("id") or "")
    text = (msg.get("text") or msg.get("caption") or "").strip()
    if not chat_id:
        return

    # ── Admin chat: replies and commands ──
    if chat_id == admin_chat_id():
        if text.startswith("/close"):
            m = re.search(r"(\d+)", text)
            t = SupportTicket.objects.filter(pk=m.group(1)).first() if m else None
            if t:
                t.status = "closed"
                t.save(update_fields=["status", "updated_at"])
                tg_send(chat_id, f"✓ Closed #{t.id}.")
            else:
                tg_send(chat_id, "Usage: /close 12")
            return
        if text.startswith("/open") or text.startswith("/tickets"):
            open_ = SupportTicket.objects.exclude(status__in=["closed", "resolved"]).order_by("-updated_at")[:15]
            lines = [f"#{t.id} {t.status} · {t.contact_label()} · {t.subject[:40]}" for t in open_]
            tg_send(chat_id, "Open questions:\n" + ("\n".join(lines) or "none 🎉"))
            return
        replied = (msg.get("reply_to_message") or {}).get("text") or ""
        ref = TICKET_REF.search(replied)
        if not ref:
            if not text.startswith("/"):
                tg_send(chat_id, "To answer someone, reply (swipe left) to their message. /open lists open questions.")
            return
        ticket = SupportTicket.objects.filter(pk=ref.group(1)).first()
        if not ticket or not text:
            return
        where = admin_reply(ticket, text, via="telegram")
        tg_send(chat_id, f"✓ Sent to #{ticket.id} by {where}." if where else f"⚠ Saved on #{ticket.id}, but they have no Telegram or email to send it to.")
        return

    # ── Anyone else talking to the bot ──
    if text.startswith("/start"):
        tg_send(chat_id, WELCOME)
        return
    if not text:
        tg_send(chat_id, "Please send your question as text.")
        return
    user = chat.get("username") or ""
    name = " ".join(p for p in (chat.get("first_name"), chat.get("last_name")) if p)
    ticket = (
        SupportTicket.objects.filter(telegram_chat_id=chat_id).exclude(status="closed").order_by("-updated_at").first()
    )
    if ticket:
        add_user_message(ticket, text, via="telegram")
    else:
        open_ticket(body=text, name=name, chat_id=chat_id, tg_username=user, via="telegram")
        tg_send(chat_id, "Got it ✓ The MixMint team will reply here.")
