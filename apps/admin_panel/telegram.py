"""Telegram support bridge: ticket alerts to admins + helpers for contact page.

Setup (owner, 5 min):
1. Telegram → chat with @BotFather → /newbot → copy token → TELEGRAM_BOT_TOKEN.
2. Chat with @userinfobot (or message your bot, then open
   https://api.telegram.org/bot<TOKEN>/getUpdates) → copy your chat id →
   TELEGRAM_ADMIN_CHAT_ID.
3. Set TELEGRAM_BOT_USERNAME (e.g. mixmint_support_bot) for the t.me deep link.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger("mixmint")


def bot_username():
    return getattr(settings, "TELEGRAM_BOT_USERNAME", "") or ""


def bot_deep_link(payload=""):
    base = f"https://t.me/{bot_username()}" if bot_username() else "https://t.me/share/url"
    return f"{base}?start={payload}" if payload and bot_username() else base


def notify_admins(text):
    """Send a plain-text alert to the admin chat. Returns True on success.

    Never raises — support flow must work even if Telegram is down.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""
    chat_id = getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", "") or ""
    if not (token and chat_id):
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text[:3500]},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        logger.exception("Telegram notify failed.")
        return False


def notify_support_ticket(ticket):
    user_label = ticket.user.full_name or ticket.user.user.email
    return notify_admins(
        "🎧 New MixMint support ticket\n"
        f"#{ticket.id} [{ticket.category}/{ticket.priority}] — {ticket.status}\n"
        f"From: {user_label}\n"
        f"Subject: {ticket.subject}\n"
        f"{ticket.description[:500]}"
    )
