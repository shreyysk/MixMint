"""MixMint Telegram bot: one bot for buyers, DJs and admins.

Who is talking is decided by the chat:
  * the admin chat (TELEGRAM_ADMIN_CHAT_ID)     -> admin commands + help-desk replies
  * a chat linked to a MixMint account          -> buyer / DJ commands
  * anyone else                                  -> browse commands + help desk

Linking: the site shows "Connect Telegram" (account settings, DJ payouts, download page). That opens
t.me/<bot>?start=ln_<profile>_<time>_<sig>; the signed link works for 2 hours and links that chat.

Notifications (all best-effort, never raise): DJ sale, payout paid/failed, release live (DJ + public
channel TELEGRAM_CHANNEL_ID), admin daily summary. Money actions from Telegram always need a second tap.
"""

import hashlib
import hmac
import logging
import time
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Count, Sum
from django.utils import timezone

logger = logging.getLogger("mixmint")
LINK_TTL = 2 * 3600


# ─────────────────────────────── plumbing ───────────────────────────────
def site():
    return (getattr(settings, "BASE_URL", "") or "https://mixmint.site").rstrip("/")


def money(v):
    try:
        v = Decimal(str(v or 0))
    except Exception:
        v = Decimal(0)
    return f"₹{v:,.0f}" if v == v.to_integral_value() else f"₹{v:,.2f}"


def send(chat_id, text, buttons=None):
    """buttons: [[(label, "https://..."), (label, "cb:data")], ...]. Returns the message or None."""
    from .support import tg

    if not chat_id:
        return None
    payload = {"chat_id": chat_id, "text": text[:3900], "disable_web_page_preview": True}
    if buttons:
        rows = []
        for row in buttons:
            r = []
            for label, target in row:
                if target.startswith("cb:"):
                    r.append({"text": label, "callback_data": target[3:][:64]})
                else:
                    r.append({"text": label, "url": target})
            rows.append(r)
        payload["reply_markup"] = {"inline_keyboard": rows}
    return send_raw(payload)


def send_raw(payload, method="sendMessage"):
    from .support import tg

    return tg(method, payload)


def chat_for(profile):
    link = getattr(profile, "telegram_link", None) if profile else None
    try:
        return link.chat_id if link else None
    except Exception:
        return None


def notify(profile, text, buttons=None):
    try:
        cid = chat_for(profile)
        return send(cid, text, buttons) if cid else None
    except Exception:
        logger.exception("Telegram notify failed")
        return None


# ─────────────────────────────── linking ───────────────────────────────
def _sig(pid, ts):
    return hmac.new(f"tg-link2:{settings.SECRET_KEY}".encode(), f"{pid}.{ts}".encode(), hashlib.sha256).hexdigest()[:12]


def link_payload(profile):
    """ln_<32 hex>_<base36 time>_<12 sig>: 56 chars, under Telegram's 64."""
    pid = str(profile.pk).replace("-", "")
    ts = _b36(int(time.time()))
    return f"ln_{pid}_{ts}_{_sig(pid, ts)}"


def link_url(profile):
    from .telegram import bot_deep_link

    return bot_deep_link(link_payload(profile))


def _b36(n):
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while n:
        n, r = divmod(n, 36)
        out = chars[r] + out
    return out or "0"


def profile_from_link(payload):
    import uuid

    from apps.accounts.models import Profile

    try:
        _, pid, ts, sig = payload.split("_", 3)
        if not hmac.compare_digest(sig, _sig(pid, ts)) or time.time() - int(ts, 36) > LINK_TTL:
            return None
        return Profile.objects.select_related("user").filter(pk=uuid.UUID(pid)).first()
    except (ValueError, TypeError):
        return None


def link_chat(profile, chat_id, username=""):
    from .models import TelegramLink

    # One account per chat: unlink this chat from any other account first.
    TelegramLink.objects.filter(chat_id=chat_id).exclude(profile=profile).delete()
    TelegramLink.objects.update_or_create(profile=profile, defaults={"chat_id": chat_id, "username": (username or "")[:64]})


def profile_for_chat(chat_id):
    from .models import TelegramLink

    link = TelegramLink.objects.select_related("profile__user").filter(chat_id=str(chat_id)).first()
    return link.profile if link else None


def connect_ctx(profile):
    """For the "Connect Telegram" card: is the bot set up, is this account linked."""
    from .telegram import bot_username

    link = None
    try:
        from .models import TelegramLink

        link = TelegramLink.objects.filter(profile=profile).first()
    except Exception:
        pass
    return {"tg_ready": bool(getattr(settings, "TELEGRAM_BOT_TOKEN", "") and bot_username()),
            "tg_linked": link is not None, "tg_username": getattr(link, "username", "") or "", "tg_bot": bot_username()}


# ─────────────────────────────── commands ───────────────────────────────
PUBLIC_COMMANDS = [
    ("start", "Menu"), ("new", "Newest releases"), ("search", "Find a release or DJ: /search name"),
    ("library", "Your purchases (linked accounts)"), ("sales", "DJs: your sales"), ("balance", "DJs: your balance and payouts"),
    ("link", "Connect this chat to your MixMint account"), ("unlink", "Disconnect this chat"), ("help", "Talk to the MixMint team"),
]
ADMIN_COMMANDS = [
    ("stats", "Today at a glance"), ("pending", "DJ applications and payouts waiting"), ("payouts", "Payouts in flight"),
    ("open", "Open help-desk questions"), ("close", "Close a question: /close 12"), ("maintenance", "/maintenance on|off|status"),
]


def menu(chat_id, profile=None):
    s = site()
    who = ""
    rows = [[("Browse releases", f"{s}/releases/"), ("Newest", "cb:new")]]
    if profile is None:
        rows.append([("Connect my MixMint account", "cb:link")])
    else:
        who = f"Hi {profile.full_name or profile.user.email.split('@')[0]}. "
        rows.append([("My purchases", "cb:library")])
        if getattr(profile, "role", "") == "dj":
            rows.append([("My sales", "cb:sales"), ("Balance", "cb:balance")])
    rows.append([("Sell on MixMint", f"{s}/sell/"), ("Talk to the team", "cb:help")])
    send(chat_id, who + "MixMint: DJ edits, remixes and packs straight from the DJs who made them. What would you like to do?", rows)


def cmd_new(chat_id):
    from apps.albums.models import AlbumPack
    from apps.tracks.models import Track

    live = dict(is_active=True, is_deleted=False, dj__status="approved", dj__profile__store_paused=False)
    items = [("track", t) for t in Track.objects.filter(**live).select_related("dj").order_by("-created_at")[:6]]
    items += [("album", a) for a in AlbumPack.objects.filter(**live).select_related("dj").order_by("-created_at")[:4]]
    items.sort(key=lambda kv: kv[1].created_at, reverse=True)
    if not items:
        return send(chat_id, "No releases yet. Check back soon.")
    lines, rows = [], []
    for kind, o in items[:6]:
        url = f"{site()}/{'tracks' if kind == 'track' else 'albums'}/{o.pk}/"
        lines.append(f"{o.title} by {o.dj.dj_name} · {money(o.price) if o.price else 'Free'}")
        rows.append([(f"{o.title[:28]} · {money(o.price) if o.price else 'Free'}", url)])
    send(chat_id, "Newest on MixMint:\n" + "\n".join(lines), rows + [[("All releases", f"{site()}/releases/")]])


def cmd_search(chat_id, q):
    from django.db.models import Q

    from apps.accounts.models import DJProfile
    from apps.tracks.models import Track

    q = (q or "").strip()[:60]
    if len(q) < 2:
        return send(chat_id, "Type what to look for, e.g. /search chai")
    live = dict(is_active=True, is_deleted=False, dj__status="approved", dj__profile__store_paused=False)
    tracks = Track.objects.filter(**live).filter(Q(title__icontains=q) | Q(genre__icontains=q) | Q(dj__dj_name__icontains=q)).select_related("dj")[:6]
    djs = DJProfile.objects.filter(status="approved", dj_name__icontains=q)[:3]
    rows = [[(f"{t.title[:28]} · {money(t.price)}", f"{site()}/tracks/{t.pk}/")] for t in tracks]
    rows += [[(f"DJ {d.dj_name}", f"{site()}/dj/{d.slug}/")] for d in djs]
    if not rows:
        return send(chat_id, f"Nothing found for “{q}”.", [[("Search on the site", f"{site()}/releases/?q={q}")]])
    send(chat_id, f"Results for “{q}”:", rows)


def cmd_library(chat_id, profile):
    from apps.albums.models import AlbumPack
    from apps.commerce.models import Purchase
    from apps.tracks.models import Track

    if profile is None:
        return need_link(chat_id)
    ps = list(Purchase.objects.filter(user=profile, status="paid", is_revoked=False).order_by("-created_at")[:8])
    if not ps:
        return send(chat_id, "No purchases yet.", [[("Browse releases", f"{site()}/releases/")]])
    names = {}
    for kind, model in (("track", Track), ("album", AlbumPack)):
        ids = [p.content_id for p in ps if p.content_type == kind]
        names.update({(kind, o.pk): o.title for o in model.objects.filter(pk__in=ids)})
    lines = [f"{names.get((p.content_type, p.content_id), 'Release')} · {p.created_at:%d %b %Y}" for p in ps]
    send(chat_id, "Your recent purchases:\n" + "\n".join(lines) + "\n\nDownloads open on your library page.",
         [[("Open my library", f"{site()}/library/")]])


def _dj(profile):
    return getattr(profile, "dj_profile", None) if profile and getattr(profile, "role", "") == "dj" else None


def cmd_sales(chat_id, profile):
    from apps.commerce.models import Purchase

    dj = _dj(profile)
    if dj is None:
        return send(chat_id, "This is for DJs with a linked MixMint account.", [[("Sell on MixMint", f"{site()}/sell/")]])
    now = timezone.now()
    out = []
    for label, since in (("Today", now.replace(hour=0, minute=0, second=0, microsecond=0)), ("7 days", now - timedelta(days=7)), ("30 days", now - timedelta(days=30))):
        agg = Purchase.objects.filter(seller=dj, status="paid", is_revoked=False, created_at__gte=since).aggregate(n=Count("id"), e=Sum("dj_earnings"))
        out.append(f"{label}: {agg['n'] or 0} sale{'s' if (agg['n'] or 0) != 1 else ''}, you earned {money(agg['e'])}")
    send(chat_id, "Your sales\n" + "\n".join(out), [[("Open dashboard", f"{site()}/dashboard/dj/")]])


def cmd_balance(chat_id, profile):
    from apps.commerce.models import DJWallet, Payout

    dj = _dj(profile)
    if dj is None:
        return send(chat_id, "This is for DJs with a linked MixMint account.")
    w, _ = DJWallet.objects.get_or_create(dj=dj)
    last = Payout.objects.filter(dj=dj).order_by("-created_at").first()
    lines = [f"Ready to receive: {money(w.available_for_payout)}", f"On hold for refunds: {money(getattr(w, 'escrow_amount', 0))}",
             f"Earned in total: {money(w.total_earnings)}"]
    if last:
        state = {"completed": "paid", "processing": "on its way", "pending": "requested", "failed": "failed, money back in balance",
                 "held": "on hold"}.get(last.status, last.status)
        lines.append(f"Last payout: {money(last.amount)} on {last.created_at:%d %b}, {state}" + (f" (UTR {last.utr})" if last.utr else ""))
    send(chat_id, "\n".join(lines), [[("Receive payment", f"{site()}/dashboard/dj/payouts/")]])


def need_link(chat_id):
    send(chat_id, "Connect this chat to your MixMint account first: open the link from Account settings on the site "
                  "(Connect Telegram). It works for 2 hours.", [[("Account settings", f"{site()}/account/")]])


# ─────────────────────────────── admin ───────────────────────────────
def admin_stats(chat_id, yesterday=False, plans=False):
    from apps.accounts.models import DJProfile, User
    from apps.commerce.models import Payout, Purchase

    from .models import SupportTicket

    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    end = None
    if yesterday:
        start, end = start - timedelta(days=1), start
    window = dict(created_at__gte=start, **({"created_at__lt": end} if end else {}))
    paid = Purchase.objects.filter(status="paid", **window)
    agg = paid.aggregate(n=Count("id"), g=Sum("price_paid"), c=Sum("commission"))
    joined = User.objects.filter(date_joined__gte=start, **({"date_joined__lt": end} if end else {})).count()
    lines = [
        f"{'Yesterday' if yesterday else 'Today'} ({start:%d %b})",
        f"Orders: {agg['n'] or 0} · sales {money(agg['g'])} · MixMint share {money(agg['c'])}",
        f"New users: {joined}",
        f"DJ applications waiting: {DJProfile.objects.filter(status__in=('pending', 'pending_review')).count()}",
        f"Payouts waiting for you: {Payout.objects.filter(status='pending', hold_reason__startswith='Waiting for admin approval').count()}"
        f" · in flight: {Payout.objects.filter(status='processing').count()}",
        f"Open questions: {SupportTicket.objects.exclude(status__in=['closed', 'resolved']).count()}",
    ]
    extra = ""
    if plans:
        try:
            from .plan_watch import telegram_lines

            extra = telegram_lines()
        except Exception:
            logger.exception("Plan check failed")
    send(chat_id, "\n".join(lines) + extra, [[("Admin", f"{site()}/api/v1/admin/dashboard/")]])


def admin_pending(chat_id):
    from apps.accounts.models import DJProfile
    from apps.commerce.models import Payout

    apps_ = DJProfile.objects.filter(status__in=["pending", "pending_review"]).select_related("profile__user").order_by("created_at")[:8]
    pays = Payout.objects.filter(status="pending").select_related("dj").order_by("created_at")[:8]
    if not apps_ and not pays:
        return send(chat_id, "Nothing waiting.")
    if apps_:
        send(chat_id, "DJ applications:\n" + "\n".join(f"{d.dj_name} · {d.profile.user.email}" for d in apps_),
             [[("Review applications", f"{site()}/api/v1/admin/dj/management/")]])
    for p in pays:
        why = (p.hold_reason or "").replace("Waiting for admin approval: ", "") or "manual payout"
        send(chat_id, f"Payout #{p.id}: {money(p.amount)} to {p.dj.dj_name} ({why}).",
             [[(f"Send {money(p.amount)}", f"cb:pay:{p.id}"), ("Open", f"{site()}/api/v1/admin/payouts/")]])


def admin_payouts(chat_id):
    from apps.commerce.models import Payout

    rows = Payout.objects.filter(status__in=["processing", "pending"]).select_related("dj").order_by("-created_at")[:12]
    if not rows:
        return send(chat_id, "No payouts in flight.")
    send(chat_id, "Payouts:\n" + "\n".join(f"#{p.id} {money(p.amount)} {p.dj.dj_name} · {p.status}{' via ' + p.provider if p.provider else ''}" for p in rows),
         [[("Check status with provider", "cb:paysync"), ("Open", f"{site()}/api/v1/admin/payouts/")]])


def admin_maintenance(chat_id, arg):
    from django.core.cache import cache

    from .models import MaintenanceMode

    arg = (arg or "status").strip().lower()
    current = MaintenanceMode.objects.order_by("-id").first()
    if arg in ("on", "off"):
        MaintenanceMode.objects.create(mode="maintenance" if arg == "on" else "normal",
                                       message="We're upgrading MixMint. Back soon." if arg == "on" else "")
        cache.delete("platform_mode")
        return send(chat_id, "Shop closed for maintenance (admins can still use everything)." if arg == "on" else "Shop is open.")
    send(chat_id, f"Shop is {'closed for maintenance' if current and current.mode == 'maintenance' else 'open'}. Use /maintenance on or /maintenance off.")


# ─────────────────────────────── dispatch ───────────────────────────────
def handle_command(chat_id, chat, text):
    """Returns True when the message was a bot command (handled here)."""
    from .support import admin_chat_id

    if not text.startswith("/"):
        return False
    word, _, arg = text.partition(" ")
    cmd = word[1:].split("@", 1)[0].lower()
    is_admin = str(chat_id) == admin_chat_id()

    if cmd == "start" and arg.startswith("ln_"):
        profile = profile_from_link(arg.strip())
        if profile is None:
            send(chat_id, "That link has expired or isn't valid. Open Connect Telegram again on mixmint.site.")
        else:
            link_chat(profile, str(chat_id), chat.get("username", ""))
            send(chat_id, "Connected to your MixMint account. You'll get your download links"
                 + (", sales and payouts" if getattr(profile, "role", "") == "dj" else "") + " here.")
            menu(chat_id, profile)
        return True
    if cmd == "start" and (arg.strip() == "help" or arg.startswith("ticket_")):
        return False  # "Talk to us" links from the help pages: the help desk greets them
    if cmd == "start" and arg.startswith("dl_"):
        send(chat_id, "That link is from an older version and no longer works. Open Connect Telegram again on mixmint.site.")
        return True
    if is_admin and cmd in ("stats",):
        admin_stats(chat_id)
        return True
    if is_admin and cmd == "pending":
        admin_pending(chat_id)
        return True
    if is_admin and cmd == "payouts":
        admin_payouts(chat_id)
        return True
    if is_admin and cmd == "maintenance":
        admin_maintenance(chat_id, arg)
        return True
    if is_admin and cmd in ("open", "tickets", "close"):
        return False  # help-desk commands live in support.handle_update
    profile = None if is_admin else profile_for_chat(chat_id)
    if cmd in ("start", "menu"):
        menu(chat_id, profile)
    elif cmd == "new":
        cmd_new(chat_id)
    elif cmd == "search":
        cmd_search(chat_id, arg)
    elif cmd in ("library", "orders"):
        cmd_library(chat_id, profile)
    elif cmd == "sales":
        cmd_sales(chat_id, profile)
    elif cmd in ("balance", "payout", "payouts"):
        cmd_balance(chat_id, profile)
    elif cmd == "link":
        need_link(chat_id) if profile is None else send(chat_id, "This chat is already connected. /unlink to disconnect.")
    elif cmd == "unlink":
        from .models import TelegramLink

        n, _ = TelegramLink.objects.filter(chat_id=str(chat_id)).delete()
        send(chat_id, "Disconnected." if n else "This chat wasn't connected.")
    elif cmd == "help":
        send(chat_id, "Type your question here and the MixMint team will reply in this chat.")
    else:
        send(chat_id, "I didn't get that. Try /start for the menu." + (" Admin: /stats /pending /payouts /open /maintenance" if is_admin else ""))
    return True


def handle_callback(cq):
    """Inline button taps. Money actions need a second tap ("confirm")."""
    from .support import admin_chat_id, tg

    data = cq.get("data") or ""
    msg = cq.get("message") or {}
    chat_id = str((msg.get("chat") or {}).get("id") or "")
    tg("answerCallbackQuery", {"callback_query_id": cq.get("id")})
    if not chat_id:
        return
    is_admin = chat_id == admin_chat_id()
    profile = None if is_admin else profile_for_chat(chat_id)
    if data == "new":
        cmd_new(chat_id)
    elif data == "library":
        cmd_library(chat_id, profile)
    elif data == "sales":
        cmd_sales(chat_id, profile)
    elif data == "balance":
        cmd_balance(chat_id, profile)
    elif data == "link":
        need_link(chat_id)
    elif data == "help":
        send(chat_id, "Type your question here and the MixMint team will reply in this chat.")
    elif is_admin and data == "paysync":
        from apps.commerce.payout_gateway import sync_processing

        r = sync_processing()
        send(chat_id, f"Checked {r['checked']}: {r['paid']} paid, {r['failed']} failed.")
    elif is_admin and data.startswith("pay:"):
        pid = data.split(":", 1)[1]
        from apps.commerce.models import Payout

        p = Payout.objects.filter(pk=pid if pid.isdigit() else 0, status="pending").select_related("dj").first()
        if p:
            send(chat_id, f"Send {money(p.amount)} to {p.dj.dj_name} now?", [[("Yes, send it", f"cb:paygo:{p.id}"), ("No", "cb:noop")]])
    elif is_admin and data.startswith("paygo:"):
        from apps.commerce.payout_gateway import active_provider, dispatch

        pid = data.split(":", 1)[1]
        if active_provider() is None:
            send(chat_id, "Automatic payouts are off or the provider keys are missing (Admin → Settings).")
        elif pid.isdigit():
            out = dispatch(int(pid), approved_by="telegram-admin")
            send(chat_id, {"completed": f"Payout #{pid} sent and confirmed.", "processing": f"Payout #{pid} sent; waiting for the bank.",
                           "failed": f"Payout #{pid} was declined; money is back in the DJ's balance."}.get(out, f"Payout #{pid}: {out}"))


# ─────────────────────────────── notifications ───────────────────────────────
def notify_sale(purchase):
    """DJ: you made a sale (Telegram + email). Called after a purchase is fulfilled."""
    try:
        seller = purchase.seller
        if seller is None:
            return
        from apps.albums.models import AlbumPack
        from apps.tracks.models import Track

        model = Track if purchase.content_type == "track" else AlbumPack
        item = model.objects.filter(pk=purchase.content_id).first()
        title = item.title if item else "your release"
        notify(seller.profile, f"New sale: {title}. You earned {money(purchase.dj_earnings)}.",
               [[("My sales", "cb:sales"), ("Balance", "cb:balance")]])
        try:
            from apps.accounts.models import NotificationPreference
            from apps.core.email_service import EmailService

            pref = NotificationPreference.objects.filter(user=seller.profile).first()
            if pref is None or pref.email_sales:
                EmailService.send_notice(
                    seller.profile.user.email, f"You made a sale: {title}", "New sale on MixMint",
                    [f"Someone just bought {title}.", f"You earned {money(purchase.dj_earnings)}. It moves to Ready to receive after the refund window."],
                    cta_label="See your sales", cta_path="/dashboard/dj/")
        except Exception:
            logger.exception("Sale email failed for purchase %s", purchase.pk)
    except Exception:
        logger.exception("Sale notification failed")


def notify_payout(payout, ok):
    text = (f"Payout sent: {money(payout.amount)}" + (f" (UTR {payout.utr})" if payout.utr else "") + ". It usually shows within minutes."
            if ok else f"Your payout of {money(payout.amount)} didn't go through ({payout.failure_reason or 'declined'}). "
                       "The money is back in your balance; check your payout details and try again.")
    notify(payout.dj.profile, text, [[("Payouts", f"{site()}/dashboard/dj/payouts/")]])


def post_release(item, kind):
    """A new release went live: tell the DJ and post it to the public channel (TELEGRAM_CHANNEL_ID)."""
    try:
        if item.dj.status != "approved" or getattr(item.dj.profile, "store_paused", False):
            return
        url = f"{site()}/{'tracks' if kind == 'track' else 'albums'}/{item.pk}/"
        price = money(item.price) if item.price else "Free"
        channel = getattr(settings, "TELEGRAM_CHANNEL_ID", "") or ""
        text = f"New on MixMint: {item.title} by {item.dj.dj_name} · {price}"
        if channel:
            cover = str(getattr(item, "cover_url", "") or getattr(item, "cover_image", "") or "")
            buttons = {"inline_keyboard": [[{"text": f"Preview and buy · {price}", "url": url}]]}
            if cover.startswith("https://"):
                send_raw({"chat_id": channel, "photo": cover, "caption": text, "reply_markup": buttons}, method="sendPhoto")
            else:
                send_raw({"chat_id": channel, "text": text, "reply_markup": buttons})
        notify(item.dj.profile, f"Your release is live: {item.title}. Share it!", [[("Open release", url)]])
    except Exception:
        logger.exception("Release post failed")


def daily_summary():
    from .support import admin_chat_id

    if admin_chat_id():
        admin_stats(admin_chat_id(), yesterday=True, plans=True)


def register_commands():
    """Command menus: everyone, and a longer one in the admin chat."""
    from .support import admin_chat_id, tg

    tg("setMyCommands", {"commands": [{"command": c, "description": d} for c, d in PUBLIC_COMMANDS]})
    if admin_chat_id():
        tg("setMyCommands", {"commands": [{"command": c, "description": d} for c, d in ADMIN_COMMANDS + [("start", "Menu")]],
                             "scope": {"type": "chat", "chat_id": admin_chat_id()}})


def setup(base_url):
    """Register the webhook, command menus and the bot's profile text."""
    from .support import set_webhook, tg

    ok, url = set_webhook(base_url)
    tg("setMyDescription", {"description": "Buy DJ edits, remixes and packs from India's DJs. Get your downloads, "
                                           "sales and payout alerts, and talk to the MixMint team."})
    tg("setMyShortDescription", {"short_description": "MixMint: Home of DJ Releases"})
    return ok, url
