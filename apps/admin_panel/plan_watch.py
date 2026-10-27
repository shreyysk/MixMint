"""When to move each service off its free plan, and what it costs.

Measured here: emails sent (counted by apps.core.mailer, per provider and in total), database size, live sales.
Shown in Admin → Settings → "Plans and costs" and added to the daily Telegram summary when something needs action.
Prices checked October 2026; confirm on each provider's pricing page before paying.
"""

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

PLANS = {
    "vercel": {"name": "Vercel Pro", "cost": "$20/month (about ₹1,700)", "url": "https://vercel.com/pricing", "billing": "https://vercel.com/account/billing",
               "why": "Hobby is for personal, non-commercial sites only. A shop taking real payments needs Pro."},
    "supabase": {"name": "Supabase Pro", "cost": "$25/month (about ₹2,100)", "url": "https://supabase.com/pricing", "billing": "https://supabase.com/dashboard/org/_/billing",
                 "why": "Free: 500 MB database, 5 GB egress, paused after 7 days without visits, no daily backups."},
    "resend": {"name": "Resend Pro", "cost": "$20/month (about ₹1,700)", "url": "https://resend.com/pricing", "billing": "https://resend.com/settings/billing",
               "why": "Free: 100 emails a day, 3,000 a month. Past that, mail moves to the Hostinger mailbox (SMTP_USER) if it is set, otherwise receipts and download emails stop for the day."},
    "r2": {"name": "Cloudflare R2 storage", "cost": "$0.015 per GB a month after the free 10 GB (100 GB ≈ $1.35, about ₹115); downloads are free",
           "url": "https://developers.cloudflare.com/r2/pricing/", "billing": "https://dash.cloudflare.com/?to=/:account/billing",
           "why": "Music files live here. Old files move to the Telegram vault automatically, so R2 stays small."},
    "upstash": {"name": "Upstash pay-as-you-go", "cost": "$0.20 per 100,000 commands after the free 500,000 a month",
                "url": "https://upstash.com/pricing/redis", "billing": "https://console.upstash.com/account/billing",
                "why": "Free: 500K commands a month. If it runs out the site keeps working, just slower (cache off)."},
}
EMAIL_DAY, EMAIL_MONTH, DB_MB = 100, 3000, 500


def _keys(provider=None):
    now = timezone.localtime()
    tag = f"{provider}:" if provider else ""
    return f"mail_day:{tag}{now:%Y%m%d}", f"mail_month:{tag}{now:%Y%m}"


def count_email(provider=None):
    """Count one sent email in the totals, and for its provider (resend / smtp) when given."""
    keys = list(_keys()) + (list(_keys(provider)) if provider else [])
    for key, ttl in zip(keys, [2 * 86400, 40 * 86400] * 2):
        if not cache.add(key, 1, ttl):
            try:
                cache.incr(key)
            except ValueError:
                cache.set(key, 1, ttl)


def emails(provider=None):
    day, month = _keys(provider)
    return int(cache.get(day) or 0), int(cache.get(month) or 0)


def email_capacity():
    """(per day, per month) across every configured sender; the Resend free plan when none is set."""
    from apps.core.mailer import provider_limits

    lims = provider_limits()
    if not lims:
        return EMAIL_DAY, EMAIL_MONTH
    return sum(d for d, _ in lims.values()), sum(m for _, m in lims.values())


def db_mb():
    from django.db import connection

    if connection.vendor != "postgresql":
        return None
    try:
        with connection.cursor() as c:
            c.execute("SELECT pg_database_size(current_database())")
            return round(c.fetchone()[0] / 1024 / 1024)
    except Exception:
        return None


def storage_gb():
    from django.db.models import Sum

    from apps.albums.models import AlbumPack
    from apps.tracks.models import Track

    total = 0
    for m in (Track, AlbumPack):
        try:
            total += m.objects.filter(is_deleted=False).aggregate(s=Sum("file_size"))["s"] or 0
        except Exception:
            pass
    return total / 1024 ** 3


def live_payments():
    env = (getattr(settings, "CASHFREE_PG_ENV", "") or getattr(settings, "PHONEPE_ENV", "") or "").lower()
    return env == "production"


def status():
    """List of {key, name, cost, why, url, level: ok|soon|now, reason}."""
    from apps.commerce.models import Purchase

    out = []
    month_start = timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    paid_month = Purchase.objects.filter(status="paid", created_at__gte=month_start).count()

    def add(key, level, reason):
        out.append({**PLANS[key], "key": key, "level": level, "reason": reason})

    if live_payments() and paid_month:
        add("vercel", "now", f"You're taking real payments ({paid_month} paid order{'s' if paid_month != 1 else ''} this month).")
    elif live_payments():
        add("vercel", "soon", "Live payment keys are on. Upgrade before your first real sale.")
    else:
        add("vercel", "ok", "Still on test payments.")

    size = db_mb()
    if size is not None and size >= DB_MB * 0.8:
        add("supabase", "now", f"Database is {size} MB of {DB_MB} MB.")
    elif (size is not None and size >= DB_MB * 0.5) or paid_month >= 100:
        add("supabase", "soon", f"Database {size if size is not None else '?'} MB of {DB_MB} MB, {paid_month} paid orders this month. Pro adds daily backups, which matter once real money moves.")
    else:
        add("supabase", "ok", f"Database {size if size is not None else '?'} MB of {DB_MB} MB.")

    day, month = emails()
    cap_day, cap_month = email_capacity()
    from apps.core.mailer import smtp_ready

    backup = ""
    if smtp_ready():
        sd, sm = emails("smtp")
        backup = f" Hostinger backup: {sd} today, {sm} this month."
    if day >= cap_day * 0.8 or month >= cap_month * 0.8:
        add("resend", "now", f"{day} emails today (limit {cap_day}), {month} this month (limit {cap_month}).{backup}")
    elif day >= cap_day * 0.5 or month >= cap_month * 0.5:
        add("resend", "soon", f"{day} emails today, {month} this month.{backup}")
    else:
        add("resend", "ok", f"{day} emails today, {month} this month.{backup}")

    gb = storage_gb()
    if gb >= 9:
        add("r2", "now", f"{gb:.1f} GB of music stored (free up to 10 GB). Add a card in Cloudflare → R2 so uploads never stop.")
    elif gb >= 6:
        add("r2", "soon", f"{gb:.1f} GB of 10 GB free.")
    else:
        add("r2", "ok", f"{gb:.1f} GB of 10 GB free.")

    add("upstash", "ok", "Check usage at console.upstash.com once a month; add a card for pay-as-you-go when you're near 500K.")
    return out


def alerts():
    return [s for s in status() if s["level"] != "ok"]


def telegram_lines():
    rows = alerts()
    if not rows:
        return ""
    return "\n\nPlans to upgrade:\n" + "\n".join(
        f"{'NOW' if r['level'] == 'now' else 'Soon'}: {r['name']}, {r['cost']}. {r['reason']}" for r in rows)
