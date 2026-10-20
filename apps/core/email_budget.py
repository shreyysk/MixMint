"""Make every Resend email count (free plan: 100 a day, 3,000 a month).

Every outgoing email (Django mail backend and email_utils.send_email) asks `route()` first:

  critical  sign-in links, codes, password, receipts, download links, refunds  -> always sent (until the hard cap)
  normal    everything not listed elsewhere                                     -> sent while under 85% of the day / 90% of the month
  low       welcome, milestones, referrals, sale notices, holds                 -> sent while under 50% of the day / 60% of the month
  admin     alerts to the admin address                                         -> go to the admin Telegram chat instead

Savings before any budget check:
  * Not critical and the person has Telegram linked: the message goes to Telegram instead (free).
  * Same person + same subject again within 15 minutes: dropped (repeat alerts, double clicks).
Skipped emails are counted (`saved()`) and shown on Admin → Settings → Plans and costs.
"""

import hashlib
import html as _html
import logging
import re

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("mixmint")

CRITICAL = re.compile(r"sign.?in|log.?in link|password|verif|\bcode\b|otp|recover|receipt|your purchase|your order|"
                      r"download is ready|refund|security|confirm your|reset", re.I)
LOW = re.compile(r"welcome|milestone|referral|made a sale|sales (today|yesterday)|your sales|earnings hold|tips|"
                 r"announcement|newsletter", re.I)
IMPORTANT = re.compile(r"approved|application|removed|payout|hold released|invoice", re.I)  # never "low"
# The bot already sends these to linked chats itself: no need to forward the email too.
COVERED = re.compile(r"made a sale|payout|is live", re.I)
DEDUPE_SECONDS = 15 * 60


def limits():
    return int(getattr(settings, "RESEND_DAILY_LIMIT", 100) or 100), int(getattr(settings, "RESEND_MONTHLY_LIMIT", 3000) or 3000)


def kind_of(to, subject):
    admins = {e.lower() for e in _admin_emails()}
    if to and to.lower() in admins and not CRITICAL.search(subject or ""):
        return "admin"
    if CRITICAL.search(subject or ""):
        return "critical"
    if LOW.search(subject or "") and not IMPORTANT.search(subject or ""):
        return "low"
    return "normal"


def _admin_emails():
    out = []
    for name in ("ADMIN_ALERT_EMAIL", "ADMIN_EMAIL", "ADMIN_NOTIFICATION_EMAIL", "SUPPORT_ALERT_EMAIL"):
        v = getattr(settings, name, "") or ""
        if isinstance(v, str) and "@" in v:
            out.append(v)
    out += [a[1] for a in (getattr(settings, "ADMINS", None) or []) if len(a) > 1]
    return out


def _count(key, ttl=40 * 86400):
    if not cache.add(key, 1, ttl):
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, ttl)


def saved():
    """Emails not sent this month because Telegram, dedupe or the budget handled them."""
    from django.utils import timezone

    return int(cache.get(f"email_saved:{timezone.now():%Y-%m}") or 0)


def _skip(reason, to, subject):
    from django.utils import timezone

    _count(f"email_saved:{timezone.now():%Y-%m}")
    logger.info("Email not sent (%s): %s", reason, (subject or "")[:80])
    return False


def _plain(html, text):
    if text:
        return text
    s = re.sub(r"(?is)<(script|style).*?</\1>", "", html or "")
    s = re.sub(r"(?i)<a [^>]*href=['\"]([^'\"]+)['\"][^>]*>(.*?)</a>", r"\2: \1", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</h\d>|</li>|</tr>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = _html.unescape(s)
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", s)).strip()


def _telegram_chat(email):
    try:
        from apps.admin_panel.models import TelegramLink

        link = TelegramLink.objects.filter(profile__user__email__iexact=email).only("chat_id").first()
        return link.chat_id if link else None
    except Exception:
        return None


def _to_telegram(chat_id, subject, html, text):
    try:
        from apps.admin_panel import bot

        return bot.send(chat_id, f"✉️ {subject}\n\n{_plain(html, text)}"[:3900]) is not None
    except Exception:
        return False


def route(to_list, subject, html="", text=""):
    """True = send this email through Resend now. False = handled another way (or not worth it)."""
    from apps.admin_panel.plan_watch import emails

    to = (to_list[0] if to_list else "") or ""
    kind = kind_of(to, subject)
    if kind == "critical":
        day, month = emails()
        d_lim, m_lim = limits()
        if day >= d_lim or month >= m_lim:
            logger.error("Resend limit reached: critical email not sent (%s)", (subject or "")[:60])
            return _skip("hard limit", to, subject)
        return True

    key = "email_dedupe:" + hashlib.sha1(f"{to.lower()}|{subject}".encode()).hexdigest()[:24]
    if not cache.add(key, 1, DEDUPE_SECONDS):
        return _skip("duplicate", to, subject)

    if kind == "admin":
        from apps.admin_panel.support import admin_chat_id

        if admin_chat_id() and _to_telegram(admin_chat_id(), subject, html, text):
            return _skip("admin telegram", to, subject)
        kind = "normal"

    if len(to_list or []) == 1:
        chat = _telegram_chat(to)
        if chat and COVERED.search(subject or ""):
            return _skip("telegram (bot sent it)", to, subject)
        if chat and _to_telegram(chat, subject, html, text):
            return _skip("telegram", to, subject)

    day, month = emails()
    d_lim, m_lim = limits()
    share = (0.5, 0.6) if kind == "low" else (0.85, 0.9)
    if day >= d_lim * share[0] or month >= m_lim * share[1]:
        return _skip(f"budget ({kind})", to, subject)
    return True
