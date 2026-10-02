"""
Admin console pages: everything an admin needs, on the website itself (no Django admin, no shell).

    Users      search every account, open one, freeze / ban / sign-in link / password reset /
               log out everywhere / Pro / admin rights / edit name & email
    Orders     every purchase with filters and totals; recheck payment, refund, free re-download,
               revoke / restore access, resend library link
    Catalog    every track, album pack and bundle; hide / show, edit, remove / restore
    Reports    content and copyright reports: dismiss, resolve, or resolve and hide the release
    Waitlist   sign-ups, delete, CSV
    Messages   in-app notice and/or email to buyers, DJs, everyone or one address
    Activity   admin action log, payment webhooks, fraud alerts
    Settings   maintenance mode, invoice generation, links to the other switches
    Export     CSV of users, orders, payouts, DJs, waitlist
    Search     one box across users, orders and releases

Every change is written to the audit log (Activity page).
"""

import csv
import logging
from datetime import timedelta
from decimal import Decimal
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.html import escape, linebreaks

from apps.accounts.models import DJProfile, InAppNotification, LoginHistory, Profile, UserDevice, Waitlist
from apps.albums.models import AlbumPack
from apps.commerce.models import Bundle, Payout, Purchase, RefundRequest, WebhookLog
from apps.core.net import get_client_ip
from apps.commerce import payout_gateway
from apps.core.genres import GENRES
from apps.tracks.models import Track

from .models import AuditLog, ContentReport, CopyrightReport, FraudAlert, MaintenanceMode, SupportTicket, SystemSetting

logger = logging.getLogger("mixmint")
User = get_user_model()
KINDS = {"track": Track, "album": AlbumPack, "bundle": Bundle}
PER_PAGE = 50


# ─────────────────────────────── helpers ───────────────────────────────
def staff_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/login/?next={request.path}")
        if not (request.user.is_active and request.user.is_staff):
            return HttpResponseForbidden("Admins only.")
        return view(request, *args, **kwargs)

    return wrapper


def _log(request, action, target_id=None, **meta):
    try:
        AuditLog.objects.create(
            admin=request.user.profile, action=action[:2000], target_id=target_id, metadata=meta or {},
            ip_address=get_client_ip(request), user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )
    except Exception:
        logger.exception("Audit log write failed")


def _page(request, qs, per=PER_PAGE):
    return Paginator(qs, per).get_page(request.GET.get("page") or 1)


def _qs_without_page(request):
    q = request.GET.copy()
    q.pop("page", None)
    return q.urlencode()


def _title(content_type, content_id):
    model = KINDS.get(content_type)
    obj = model.objects.filter(pk=content_id).only("title").first() if model else None
    return obj.title if obj else "(removed)"


def _titles(purchases):
    """{(type, id): title} for a page of purchases in three queries, not one per row."""
    want = {}
    for p in purchases:
        want.setdefault(p.content_type, set()).add(p.content_id)
    out = {}
    for kind, ids in want.items():
        model = KINDS.get(kind)
        if model:
            for pk, title in model.objects.filter(pk__in=ids).values_list("pk", "title"):
                out[(kind, pk)] = title
    return out


def _csv_response(filename, header, rows):
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    resp.write("﻿")  # Excel opens UTF-8 (₹, names) correctly
    w = csv.writer(resp)
    w.writerow(header)
    for r in rows:
        w.writerow(["" if v is None else v for v in r])
    return resp


def _profile_for(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


# ─────────────────────────────── search ───────────────────────────────
@staff_required
def search_view(request):
    q = (request.GET.get("q") or "").strip()
    users = orders = tracks = albums = bundles = []
    if len(q) >= 2:
        users = User.objects.filter(Q(email__icontains=q) | Q(profile__full_name__icontains=q) | Q(profile__dj_profile__dj_name__icontains=q)).select_related("profile").distinct()[:20]
        oq = Q(gateway_order_id__icontains=q) | Q(gateway_payment_id__icontains=q) | Q(user__user__email__icontains=q)
        if q.isdigit():
            oq |= Q(pk=int(q))
        orders = Purchase.objects.filter(oq).select_related("user__user").order_by("-created_at")[:20]
        tracks = Track.objects.filter(Q(title__icontains=q) | Q(dj__dj_name__icontains=q)).select_related("dj")[:20]
        albums = AlbumPack.objects.filter(Q(title__icontains=q) | Q(dj__dj_name__icontains=q)).select_related("dj")[:20]
        bundles = Bundle.objects.filter(Q(title__icontains=q) | Q(dj__dj_name__icontains=q)).select_related("dj")[:20]
    titles = _titles(orders) if orders else {}
    for o in orders:
        o.item_title = titles.get((o.content_type, o.content_id), "(removed)")
    return render(request, "admin/console/search.html", {
        "q": q, "users": users, "orders": orders, "tracks": tracks, "albums": albums, "bundles": bundles,
        "nothing": len(q) >= 2 and not any([users, orders, tracks, albums, bundles]),
    })


# ─────────────────────────────── users ───────────────────────────────
def _users_qs(request):
    qs = User.objects.select_related("profile").order_by("-date_joined")
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(profile__full_name__icontains=q) | Q(profile__dj_profile__dj_name__icontains=q)).distinct()
    role = request.GET.get("role")
    if role == "buyer":
        qs = qs.filter(profile__role="user", is_staff=False)
    elif role == "dj":
        qs = qs.filter(profile__role="dj")
    elif role == "admin":
        qs = qs.filter(is_staff=True)
    st = request.GET.get("status")
    if st == "frozen":
        qs = qs.filter(profile__is_frozen=True)
    elif st == "banned":
        qs = qs.filter(profile__is_banned=True)
    elif st == "inactive":
        qs = qs.filter(is_active=False)
    elif st == "pro":
        qs = qs.filter(profile__is_pro_dj=True)
    return qs


@staff_required
def users_view(request):
    page = _page(request, _users_qs(request))
    ids = [u.profile.pk for u in page if hasattr(u, "profile")]
    stats = {
        r["user"]: r for r in Purchase.objects.filter(user__in=ids, status="paid").values("user").annotate(n=Count("id"), spent=Sum("price_paid"))
    }
    for u in page:
        s = stats.get(getattr(getattr(u, "profile", None), "pk", None), {})
        u.n_orders, u.spent = s.get("n", 0), s.get("spent") or 0
    counts = {
        "all": User.objects.count(),
        "dj": Profile.objects.filter(role="dj").count(),
        "admin": User.objects.filter(is_staff=True).count(),
        "frozen": Profile.objects.filter(is_frozen=True).count(),
        "banned": Profile.objects.filter(is_banned=True).count(),
        "new_7d": User.objects.filter(date_joined__gte=timezone.now() - timedelta(days=7)).count(),
    }
    return render(request, "admin/console/users.html", {"page": page, "counts": counts, "qs": _qs_without_page(request), "f": request.GET})


def _logout_everywhere(user):
    from django.contrib.sessions.models import Session

    n = 0
    for s in Session.objects.filter(expire_date__gte=timezone.now()).iterator():
        try:
            if s.get_decoded().get("_auth_user_id") == str(user.pk):
                s.delete()
                n += 1
        except Exception:
            continue
    try:  # API tokens too
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

        for t in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=t)
    except Exception:
        pass
    return n


@staff_required
def user_detail_view(request, user_id):
    user = get_object_or_404(User.objects.select_related("profile"), pk=user_id)
    profile = _profile_for(user)
    me = request.user
    is_self = user.pk == me.pk

    if request.method == "POST":
        action = request.POST.get("action", "")
        dangerous = {"freeze", "ban", "deactivate", "revoke_admin", "logout_all"}
        if is_self and action in dangerous:
            messages.error(request, "You can't do that to your own account.")
            return redirect("admin_user_detail", user_id=user.pk)
        if user.is_superuser and not me.is_superuser and action in dangerous | {"edit"}:
            messages.error(request, "Only an owner account can change another owner.")
            return redirect("admin_user_detail", user_id=user.pk)
        reason = (request.POST.get("reason") or "").strip()[:500]

        if action in ("freeze", "unfreeze"):
            profile.is_frozen = action == "freeze"
            profile.save(update_fields=["is_frozen"])
            if profile.is_frozen:
                _logout_everywhere(user)
            _log(request, f"{action.title()} account {user.email}", reason=reason)
            messages.success(request, "Account frozen: they can't log in or buy." if profile.is_frozen else "Account unfrozen.")
        elif action in ("ban", "unban"):
            profile.is_banned = action == "ban"
            profile.save(update_fields=["is_banned"])
            if profile.is_banned:
                _logout_everywhere(user)
                UserDevice.objects.filter(user=user).update(status="banned")
            else:
                UserDevice.objects.filter(user=user, status="banned").update(status="revoked")
            _log(request, f"{action.title()}ned {user.email}" if action == "ban" else f"Unbanned {user.email}", reason=reason)
            messages.success(request, "Banned. Their devices are blocked too." if profile.is_banned else "Ban lifted.")
        elif action in ("deactivate", "activate"):
            user.is_active = action == "activate"
            user.save(update_fields=["is_active"])
            if not user.is_active:
                _logout_everywhere(user)
            _log(request, f"{'Reactivated' if user.is_active else 'Deactivated'} {user.email}", reason=reason)
            messages.success(request, "Account switched off." if not user.is_active else "Account switched back on.")
        elif action == "logout_all":
            n = _logout_everywhere(user)
            _log(request, f"Logged {user.email} out everywhere")
            messages.success(request, f"Logged out of {n} browser session{'s' if n != 1 else ''}.")
        elif action == "revoke_devices":
            n = UserDevice.objects.filter(user=user, status="authorized").update(status="revoked")
            _log(request, f"Reset download devices for {user.email}")
            messages.success(request, f"{n} device{'s' if n != 1 else ''} reset. Their next download registers the device again.")
        elif action == "signin_link":
            try:
                from apps.core.catalog_views import _send_signin_link

                _send_signin_link(request, user, "Your MixMint library", "Here's a link to get back into your MixMint library.")
                _log(request, f"Sent sign-in link to {user.email}")
                messages.success(request, f"Sign-in link emailed to {user.email} (works once, 30 minutes).")
            except Exception as exc:
                messages.error(request, f"Couldn't send the email ({type(exc).__name__}).")
        elif action == "password_reset":
            from django.contrib.auth.forms import PasswordResetForm

            form = PasswordResetForm({"email": user.email})
            if form.is_valid():
                try:
                    form.save(request=request, use_https=request.is_secure(), from_email=None)
                    _log(request, f"Sent password reset to {user.email}")
                    messages.success(request, "Password reset email sent.")
                except Exception as exc:
                    messages.error(request, f"Couldn't send the email ({type(exc).__name__}).")
        elif action == "verify_email":
            user.email_verified = not user.email_verified
            user.save(update_fields=["email_verified"])
            _log(request, f"Marked {user.email} email as {'verified' if user.email_verified else 'unverified'}")
            messages.success(request, "Email marked verified." if user.email_verified else "Email marked unverified.")
        elif action == "edit":
            name = (request.POST.get("full_name") or "").strip()[:255]
            email = (request.POST.get("email") or "").strip().lower()[:254]
            if email and email != user.email:
                if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
                    messages.error(request, "Another account already uses that email.")
                    return redirect("admin_user_detail", user_id=user.pk)
                old = user.email
                user.email = email
                user.save(update_fields=["email"])
                _log(request, f"Changed email {old} → {email}")
            if name != (profile.full_name or ""):
                profile.full_name = name
                profile.save(update_fields=["full_name"])
                _log(request, f"Renamed {user.email} to {name}")
            messages.success(request, "Saved.")
        elif action in ("give_pro", "end_pro"):
            if profile.role != "dj":
                messages.error(request, "Pro is for DJs.")
            elif action == "give_pro":
                try:
                    days = max(1, min(int(request.POST.get("days") or 30), 3650))
                except ValueError:
                    days = 30
                now = timezone.now()
                base = profile.pro_expires_at if profile.is_pro_dj and profile.pro_expires_at and profile.pro_expires_at > now else now
                profile.is_pro_dj, profile.pro_expires_at = True, base + timedelta(days=days)
                profile.pro_started_at = profile.pro_started_at or now
                profile.storage_quota_mb = max(profile.storage_quota_mb or 0, 20480)
                profile.save(update_fields=["is_pro_dj", "pro_expires_at", "pro_started_at", "storage_quota_mb"])
                _log(request, f"Gave Pro to {user.email} for {days} days", reason=reason)
                messages.success(request, f"Pro active until {profile.pro_expires_at:%d %b %Y}.")
            else:
                profile.is_pro_dj = False
                profile.pro_expires_at = timezone.now()
                profile.save(update_fields=["is_pro_dj", "pro_expires_at"])
                _log(request, f"Ended Pro for {user.email}", reason=reason)
                messages.success(request, "Pro ended.")
        elif action in ("make_admin", "revoke_admin"):
            if not me.is_superuser:
                messages.error(request, "Only an owner account can change admin rights.")
            else:
                user.is_staff = action == "make_admin"
                user.save(update_fields=["is_staff"])
                _log(request, f"{'Gave' if user.is_staff else 'Removed'} admin rights {'to' if user.is_staff else 'from'} {user.email}")
                messages.success(request, "Admin rights given." if user.is_staff else "Admin rights removed.")
        elif action == "notify":
            title = (request.POST.get("title") or "").strip()[:200]
            body = (request.POST.get("message") or "").strip()[:4000]
            if title and body:
                InAppNotification.objects.create(user=profile, notification_type="system", title=title, message=body)
                if request.POST.get("also_email"):
                    _send_one(user.email, title, body)
                _log(request, f"Messaged {user.email}: {title}")
                messages.success(request, "Message sent.")
            else:
                messages.error(request, "Add a title and a message.")
        else:
            messages.error(request, "Unknown action.")
        return redirect("admin_user_detail", user_id=user.pk)

    purchases = list(Purchase.objects.filter(user=profile).order_by("-created_at")[:50])
    titles = _titles(purchases)
    for p in purchases:
        p.item_title = titles.get((p.content_type, p.content_id), "(removed)")
    agg = Purchase.objects.filter(user=profile, status="paid").aggregate(n=Count("id"), spent=Sum("price_paid"))
    dj = DJProfile.objects.filter(profile=profile).first()
    dj_stats = None
    if dj:
        sales = Purchase.objects.filter(seller=dj, status="paid", is_revoked=False)
        dj_stats = {
            "tracks": Track.objects.filter(dj=dj, is_deleted=False).count(),
            "albums": AlbumPack.objects.filter(dj=dj, is_deleted=False).count(),
            "sales": sales.count(),
            "earned": sales.aggregate(s=Sum("dj_earnings"))["s"] or 0,
            "payouts": Payout.objects.filter(dj=dj).order_by("-created_at")[:10],
        }
    return render(request, "admin/console/user_detail.html", {
        "u": user, "p": profile, "dj": dj, "dj_stats": dj_stats, "is_self": is_self,
        "purchases": purchases, "agg": agg,
        "devices": UserDevice.objects.filter(user=user).order_by("-last_active_at")[:20],
        "logins": LoginHistory.objects.filter(user=user).order_by("-created_at")[:15],
        "tickets": SupportTicket.objects.filter(Q(user=profile) | Q(guest_email__iexact=user.email)).order_by("-created_at")[:10],
        "refunds": RefundRequest.objects.filter(purchase__user=profile).select_related("purchase").order_by("-created_at")[:10],
        "actions": AuditLog.objects.filter(Q(action__icontains=user.email)).select_related("admin__user").order_by("-created_at")[:15],
        "can_owner": me.is_superuser,
    })


# ─────────────────────────────── orders ───────────────────────────────
def _orders_qs(request):
    qs = Purchase.objects.select_related("user__user", "seller").order_by("-created_at")
    q = (request.GET.get("q") or "").strip()
    if q:
        f = Q(gateway_order_id__icontains=q) | Q(gateway_payment_id__icontains=q) | Q(user__user__email__icontains=q) | Q(seller__dj_name__icontains=q)
        if q.isdigit():
            f |= Q(pk=int(q))
        qs = qs.filter(f)
    if request.GET.get("status") in ("pending", "paid", "failed", "refunded", "disputed"):
        qs = qs.filter(status=request.GET["status"])
    if request.GET.get("gateway"):
        qs = qs.filter(payment_gateway=request.GET["gateway"])
    if request.GET.get("type") in KINDS:
        qs = qs.filter(content_type=request.GET["type"])
    days = request.GET.get("days")
    if days and days.isdigit():
        qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=int(days)))
    if request.GET.get("revoked") == "1":
        qs = qs.filter(is_revoked=True)
    return qs


@staff_required
def orders_view(request):
    qs = _orders_qs(request)
    if request.GET.get("format") == "csv":
        return _export_orders(qs)
    page = _page(request, qs)
    titles = _titles(page)
    for p in page:
        p.item_title = titles.get((p.content_type, p.content_id), "(removed)")
    paid = qs.filter(status="paid", is_revoked=False).aggregate(n=Count("id"), gross=Sum("price_paid"), commission=Sum("commission"), fees=Sum("platform_fee"), dj=Sum("dj_earnings"))
    gateways = Purchase.objects.exclude(payment_gateway="").values_list("payment_gateway", flat=True).distinct()
    return render(request, "admin/console/orders.html", {
        "page": page, "paid": paid, "platform": (paid["commission"] or 0) + (paid["fees"] or 0),
        "gateways": [g for g in gateways if g], "qs": _qs_without_page(request), "f": request.GET,
        "pending_count": Purchase.objects.filter(status="pending", created_at__gte=timezone.now() - timedelta(days=2)).count(),
    })


@staff_required
def order_detail_view(request, order_id):
    p = get_object_or_404(Purchase.objects.select_related("user__user", "seller"), pk=order_id)
    if request.method == "POST":
        action = request.POST.get("action", "")
        note = (request.POST.get("note") or "").strip()[:1000]
        if action == "recheck":
            if p.status != "pending" or not p.gateway_order_id:
                messages.error(request, "Only pending orders can be rechecked.")
            else:
                try:
                    from apps.payments.views import _fulfil_from_status

                    outcome = _fulfil_from_status(p.gateway_order_id, p.payment_gateway or "razorpay")
                    _log(request, f"Rechecked payment for order #{p.pk}: {outcome}")
                    messages.success(request, {"success": "Payment confirmed — the order is now paid.",
                                               "failed": "The gateway says this payment failed.",
                                               "pending": "Still pending at the gateway."}.get(outcome, outcome))
                except Exception as exc:
                    messages.error(request, f"Couldn't reach the gateway ({type(exc).__name__}).")
        elif action == "refund":
            if p.status != "paid":
                messages.error(request, "Only paid orders can be refunded.")
            else:
                from apps.commerce.views import execute_refund

                req, _ = RefundRequest.objects.get_or_create(purchase=p, defaults={"reason": note or "Refunded by admin", "status": "pending"})
                if req.status not in ("pending", "approved"):
                    req.status = "pending"
                    req.save(update_fields=["status"])
                if execute_refund(req, note=note or f"Refunded by {request.user.email}"):
                    _log(request, f"Refunded order #{p.pk} ({p.price_paid})", note=note)
                    messages.success(request, "Refund sent. The buyer gets the money back in 5–7 working days.")
                else:
                    messages.error(request, "The payment gateway refused the refund. Check its dashboard, then try again.")
        elif action == "redownload":
            Purchase.objects.filter(pk=p.pk).update(download_completed=False)
            _log(request, f"Allowed a free re-download for order #{p.pk}")
            messages.success(request, "Done — the buyer can download it again for free.")
        elif action in ("revoke", "restore"):
            Purchase.objects.filter(pk=p.pk).update(is_revoked=action == "revoke")
            _log(request, f"{'Revoked' if action == 'revoke' else 'Restored'} access for order #{p.pk}", note=note)
            messages.success(request, "Access removed." if action == "revoke" else "Access restored.")
        elif action == "resend":
            try:
                from apps.core.catalog_views import _send_signin_link

                _send_signin_link(request, p.user.user, "Your MixMint download", "Here's a link to your MixMint library, where your download is waiting.")
                _log(request, f"Resent library link for order #{p.pk} to {p.user.user.email}")
                messages.success(request, f"Library link emailed to {p.user.user.email}.")
            except Exception as exc:
                messages.error(request, f"Couldn't send the email ({type(exc).__name__}).")
        else:
            messages.error(request, "Unknown action.")
        return redirect("admin_order_detail", order_id=p.pk)

    from apps.commerce.models import Invoice
    from apps.downloads.models import DownloadLog

    item = KINDS.get(p.content_type)
    item_obj = item.objects.filter(pk=p.content_id).first() if item else None
    hooks = WebhookLog.objects.filter(Q(transaction_id__icontains=p.gateway_order_id) if p.gateway_order_id else Q(pk__isnull=True)).order_by("-received_at")[:10]
    return render(request, "admin/console/order_detail.html", {
        "p": p, "item": item_obj, "invoice": Invoice.objects.filter(purchase=p).first(),
        "refund": RefundRequest.objects.filter(purchase=p).first(),
        "downloads": DownloadLog.objects.filter(user=p.user, content_type=p.content_type, content_id=p.content_id).order_by("-created_at")[:10],
        "hooks": hooks,
    })


# ─────────────────────────────── catalog ───────────────────────────────
def _catalog_rows(request):
    kind = request.GET.get("type") or "track"
    model = KINDS.get(kind, Track)
    qs = model.objects.select_related("dj").order_by("-created_at")
    q = (request.GET.get("q") or "").strip()
    if q:
        f = Q(title__icontains=q) | Q(dj__dj_name__icontains=q)
        if q.isdigit():
            f |= Q(pk=int(q))
        qs = qs.filter(f)
    st = request.GET.get("status")
    if st == "live":
        qs = qs.filter(is_active=True, is_deleted=False)
    elif st == "hidden":
        qs = qs.filter(is_active=False, is_deleted=False)
    elif st == "removed":
        qs = qs.filter(is_deleted=True)
    if request.GET.get("dj"):
        qs = qs.filter(dj__slug=request.GET["dj"])
    y, m = request.GET.get("year") or "", request.GET.get("month") or ""
    if y.isdigit():
        qs = qs.filter(created_at__year=int(y))
    if m.isdigit() and 1 <= int(m) <= 12:
        qs = qs.filter(created_at__month=int(m))
    genre = (request.GET.get("genre") or "").strip()
    if genre and kind == "track":
        qs = qs.filter(genre__iexact=genre)
    order = {"new": "-created_at", "old": "created_at", "title_az": "title", "title_za": "-title",
             "price_high": "-price", "price_low": "price"}
    if kind == "track":
        order.update({"downloads": "-download_count", "bpm_high": "-bpm", "bpm_low": "bpm"})
    qs = qs.order_by(order.get(request.GET.get("sort"), "-created_at"), "-pk")
    return kind, qs


@staff_required
def catalog_view(request):
    if request.method == "POST":
        kind, pk, action = request.POST.get("kind"), request.POST.get("pk"), request.POST.get("action")
        model = KINDS.get(kind)
        obj = model.objects.filter(pk=pk).first() if model and str(pk).isdigit() else None
        if obj is None:
            messages.error(request, "Not found.")
        elif action in ("hide", "show"):
            obj.is_active = action == "show"
            obj.save(update_fields=["is_active"])
            _log(request, f"{'Showed' if obj.is_active else 'Hid'} {kind} #{obj.pk} “{obj.title}”")
            messages.success(request, f"“{obj.title}” is {'live' if obj.is_active else 'hidden from the shop'}.")
        return redirect(request.POST.get("next") or "admin_catalog")
    kind, qs = _catalog_rows(request)
    page = _page(request, qs)
    for o in page:
        o.thumb = getattr(o, "cover_url", "") or getattr(o, "cover_image", "") or ""
    if kind in ("track", "album"):
        sales = {r["content_id"]: r for r in Purchase.objects.filter(content_type=kind, content_id__in=[o.pk for o in page], status="paid").values("content_id").annotate(n=Count("id"), gross=Sum("price_paid"))}
        for o in page:
            s = sales.get(o.pk, {})
            o.n_sales, o.gross = s.get("n", 0), s.get("gross") or 0
    counts = {k: m.objects.filter(is_deleted=False).count() for k, m in KINDS.items()}
    return render(request, "admin/console/catalog.html", {
        "page": page, "kind": kind, "counts": counts, "qs": _qs_without_page(request), "f": request.GET,
        "djs": DJProfile.objects.filter(status="approved").order_by("dj_name").values("slug", "dj_name"),
        "years": sorted({d.year for d in KINDS.get(kind, Track).objects.dates("created_at", "year")}, reverse=True),
        "months": list(enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)),
        "genre_list": GENRES,
    })


@staff_required
def catalog_edit_view(request, kind, pk):
    model = KINDS.get(kind)
    if not model:
        return redirect("admin_catalog")
    obj = get_object_or_404(model.objects.select_related("dj"), pk=pk)
    if request.method == "POST":
        action = request.POST.get("action", "save")
        if action in ("remove", "restore"):
            obj.is_deleted = action == "remove"
            fields = ["is_deleted"]
            if hasattr(obj, "deleted_at"):
                obj.deleted_at = timezone.now() if obj.is_deleted else None
                fields.append("deleted_at")
            obj.save(update_fields=fields)
            reason = (request.POST.get("reason") or "").strip()[:500]
            if obj.is_deleted:
                try:
                    InAppNotification.objects.create(
                        user=obj.dj.profile, notification_type="system", title=f"“{obj.title}” was removed",
                        message=reason or "An admin removed this release from MixMint. Reply through Help if you think this is a mistake.",
                    )
                except Exception:
                    pass
            _log(request, f"{'Removed' if obj.is_deleted else 'Restored'} {kind} #{obj.pk} “{obj.title}”", reason=reason)
            messages.success(request, "Removed from MixMint (buyers keep access)." if obj.is_deleted else "Restored.")
            return redirect("admin_catalog_edit", kind=kind, pk=obj.pk)

        changed = []

        def put(field, value):
            if hasattr(obj, field) and getattr(obj, field) != value:
                setattr(obj, field, value)
                changed.append(field)

        title = (request.POST.get("title") or "").strip()[:255]
        if title:
            put("title", title)
        put("description", (request.POST.get("description") or "").strip()[:5000])
        for f in ("price", "compare_at_price"):
            raw = (request.POST.get(f) or "").strip()
            if f == "compare_at_price" and raw == "":
                put(f, None)
            elif raw:
                try:
                    v = Decimal(raw).quantize(Decimal("0.01"))
                    if v < 0 or v > 100000:
                        raise ValueError
                    put(f, v)
                except Exception:
                    messages.error(request, f"{'Price' if f == 'price' else 'Was-price'} must be a number from 0 to 100000.")
                    return redirect("admin_catalog_edit", kind=kind, pk=obj.pk)
        if hasattr(obj, "genre"):
            put("genre", (request.POST.get("genre") or "").strip()[:100])
        raw = (request.POST.get("copies_limit") or "").strip()
        if hasattr(obj, "copies_limit"):
            put("copies_limit", int(raw) if raw.isdigit() and int(raw) > 0 else None)
        for f in ("youtube_url", "instagram_url"):
            if hasattr(obj, f) and f in request.POST:
                put(f, (request.POST.get(f) or "").strip()[:500])
        put("is_active", bool(request.POST.get("is_active")))
        if changed:
            obj.save(update_fields=changed)
            _log(request, f"Edited {kind} #{obj.pk} “{obj.title}”: {', '.join(changed)}")
            messages.success(request, "Saved.")
        else:
            messages.info(request, "Nothing changed.")
        return redirect("admin_catalog_edit", kind=kind, pk=obj.pk)

    sales = Purchase.objects.filter(content_type=kind, content_id=obj.pk) if kind != "bundle" else Purchase.objects.none()
    vault = None
    if kind in ("track", "album"):
        from .models import VaultFile

        vault = VaultFile.objects.filter(content_type=kind, content_id=obj.pk).first()
    reports = ContentReport.objects.filter(content_type=kind, content_id=obj.pk).order_by("-created_at")[:10] if kind != "bundle" else []
    return render(request, "admin/console/catalog_edit.html", {
        "o": obj, "kind": kind, "vault": vault, "reports": reports,
        "sales": sales.filter(status="paid").aggregate(n=Count("id"), gross=Sum("price_paid")),
        "recent_sales": sales.select_related("user__user").order_by("-created_at")[:10],
        "public_url": {"track": f"/tracks/{obj.pk}/", "album": f"/albums/{obj.pk}/", "bundle": f"/bundles/{obj.pk}/"}[kind],
    })


# ─────────────────────────────── reports ───────────────────────────────
@staff_required
def reports_view(request):
    if request.method == "POST":
        src, rid, action = request.POST.get("src"), request.POST.get("id"), request.POST.get("action")
        note = (request.POST.get("note") or "").strip()[:1000]
        model = ContentReport if src == "content" else CopyrightReport
        r = model.objects.filter(pk=rid).first() if str(rid).isdigit() else None
        if r is None:
            messages.error(request, "Report not found.")
            return redirect("admin_reports")
        item = None
        if src == "content":
            item = KINDS[r.content_type].objects.filter(pk=r.content_id).first()
        else:
            item = r.track or r.album
        if action == "takedown" and item is not None:
            item.is_active = False
            item.save(update_fields=["is_active"])
            try:
                InAppNotification.objects.create(
                    user=item.dj.profile, notification_type="system", title=f"“{item.title}” was hidden after a report",
                    message=note or "We hid this release after a report. Reply through Help to sort it out.",
                )
            except Exception:
                pass
        new = "dismissed" if action == "dismiss" else "resolved"
        r.status, r.admin_notes = new, note or r.admin_notes
        fields = ["status", "admin_notes"]
        if hasattr(r, "resolved_at"):
            r.resolved_at = timezone.now()
            fields.append("resolved_at")
        r.save(update_fields=fields)
        _log(request, f"{'Dismissed' if new == 'dismissed' else 'Resolved'} {src} report #{r.pk}" + (f" and hid “{item.title}”" if action == "takedown" and item else ""), note=note)
        messages.success(request, {"dismiss": "Report dismissed.", "resolve": "Marked resolved.", "takedown": "Release hidden and report resolved."}.get(action, "Done."))
        return redirect("admin_reports")

    show = request.GET.get("show") or "open"
    cr = ContentReport.objects.select_related("reporter__user").order_by("-created_at")
    dr = CopyrightReport.objects.select_related("reporter__user", "track__dj", "album__dj").order_by("-created_at")
    if show == "open":
        cr, dr = cr.filter(status="pending"), dr.filter(status="pending")
    rows = []
    for r in cr[:200]:
        item = KINDS[r.content_type].objects.filter(pk=r.content_id).select_related("dj").first()
        rows.append({"src": "content", "r": r, "item": item, "kind": r.content_type, "label": r.get_report_type_display(), "who": r.who, "evidence": r.evidence_url})
    for r in dr[:200]:
        item = r.track or r.album
        rows.append({"src": "copyright", "r": r, "item": item, "kind": "track" if r.track_id else "album", "label": "Copyright (DMCA)", "who": r.reporter.user.email if r.reporter_id else "guest", "evidence": r.evidence_url})
    rows.sort(key=lambda x: x["r"].created_at, reverse=True)
    return render(request, "admin/console/reports.html", {"rows": rows, "show": show})


# ─────────────────────────────── waitlist ───────────────────────────────
@staff_required
def waitlist_view(request):
    if request.method == "POST" and request.POST.get("action") == "delete":
        n, _ = Waitlist.objects.filter(pk__in=request.POST.getlist("ids")).delete()
        _log(request, f"Deleted {n} waitlist sign-up(s)")
        messages.success(request, f"Deleted {n}.")
        return redirect("admin_waitlist")
    qs = Waitlist.objects.order_by("-created_at")
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(full_name__icontains=q))
    if request.GET.get("who") == "dj":
        qs = qs.filter(is_dj=True)
    elif request.GET.get("who") == "buyer":
        qs = qs.filter(is_dj=False)
    if request.GET.get("format") == "csv":
        return _csv_response("mixmint-waitlist.csv", ["email", "name", "dj", "source", "joined"],
                             ((w.email, w.full_name, "yes" if w.is_dj else "no", w.source, w.created_at.strftime("%Y-%m-%d %H:%M")) for w in qs.iterator()))
    return render(request, "admin/console/waitlist.html", {
        "page": _page(request, qs, 100), "qs": _qs_without_page(request), "f": request.GET,
        "counts": {"all": Waitlist.objects.count(), "dj": Waitlist.objects.filter(is_dj=True).count()},
    })


# ─────────────────────────────── messages ───────────────────────────────
def _email_html(title, body):
    return (f"<h2 style='font-family:sans-serif'>{escape(title)}</h2>"
            f"<div style='font-family:sans-serif;font-size:15px;line-height:1.55'>{linebreaks(escape(body))}</div>"
            "<p style='color:#888;font-size:12px;font-family:sans-serif'>— MixMint · mixmint.site</p>")


def _send_one(email, title, body):
    from .email_utils import send_email

    try:
        send_email(email, title, _email_html(title, body))
        return True
    except Exception:
        logger.exception("Admin email to %s failed", email)
        return False


def _send_batch(emails, title, body):
    """Resend's batch endpoint takes 100 emails per call. Returns how many were accepted."""
    import requests
    from django.conf import settings

    if not getattr(settings, "RESEND_API_KEY", ""):
        return 0
    sent, html = 0, _email_html(title, body)
    for i in range(0, len(emails), 100):
        chunk = emails[i:i + 100]
        try:
            r = requests.post("https://api.resend.com/emails/batch", timeout=30,
                              headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}", "Content-Type": "application/json"},
                              json=[{"from": settings.FROM_EMAIL, "to": [e], "subject": title, "html": html} for e in chunk])
            if r.status_code < 300:
                sent += len(chunk)
        except Exception:
            logger.exception("Admin batch email failed")
    return sent


def _audience(name):
    users = User.objects.filter(is_active=True, profile__is_banned=False)
    if name == "buyers":
        return users.filter(profile__role="user", is_staff=False)
    if name == "djs":
        return users.filter(profile__role="dj")
    if name == "pro":
        return users.filter(profile__is_pro_dj=True)
    if name == "buyers_paid":
        return users.filter(profile__purchases__status="paid").distinct()
    if name == "all":
        return users
    return users.none()


AUDIENCES = [("all", "Everyone"), ("buyers", "All buyers"), ("buyers_paid", "Buyers who bought something"),
             ("djs", "All DJs"), ("pro", "Pro DJs"), ("waitlist", "Waitlist (email only)"), ("one", "One email address")]


@staff_required
def messages_view(request):
    if request.method == "POST":
        aud = request.POST.get("audience")
        title = (request.POST.get("title") or "").strip()[:200]
        body = (request.POST.get("message") or "").strip()[:8000]
        in_app, by_email = bool(request.POST.get("in_app")), bool(request.POST.get("email"))
        if not title or not body or not (in_app or by_email):
            messages.error(request, "Add a subject, a message and at least one way to send it.")
            return redirect("admin_messages")
        if not request.POST.get("confirm"):
            messages.error(request, "Tick the confirmation box to send.")
            return redirect("admin_messages")
        if aud == "one":
            email = (request.POST.get("one_email") or "").strip().lower()
            u = User.objects.filter(email__iexact=email).select_related("profile").first()
            n_app = 0
            if in_app and u:
                InAppNotification.objects.create(user=_profile_for(u), notification_type="system", title=title, message=body)
                n_app = 1
            n_mail = 1 if by_email and email and _send_one(email, title, body) else 0
        elif aud == "waitlist":
            n_app = 0
            n_mail = _send_batch(list(Waitlist.objects.values_list("email", flat=True)), title, body) if by_email else 0
        else:
            users = _audience(aud).select_related("profile")
            n_app = 0
            if in_app:
                InAppNotification.objects.bulk_create(
                    [InAppNotification(user=u.profile, notification_type="system", title=title, message=body) for u in users if hasattr(u, "profile")],
                    batch_size=500,
                )
                n_app = users.count()
            n_mail = _send_batch(list(users.values_list("email", flat=True)), title, body) if by_email else 0
        _log(request, f"Sent message “{title}” to {dict(AUDIENCES).get(aud, aud)}", in_app=n_app, emails=n_mail)
        messages.success(request, f"Sent: {n_app} in-app, {n_mail} email{'s' if n_mail != 1 else ''}.")
        return redirect("admin_messages")
    sizes = {k: (_audience(k).count() if k not in ("waitlist", "one") else (Waitlist.objects.count() if k == "waitlist" else 1)) for k, _ in AUDIENCES}
    history = AuditLog.objects.filter(action__startswith="Sent message").select_related("admin__user").order_by("-created_at")[:20]
    from django.conf import settings

    return render(request, "admin/console/messages.html", {
        "audiences": [(k, label, sizes[k]) for k, label in AUDIENCES], "history": history,
        "email_ready": bool(getattr(settings, "RESEND_API_KEY", "")),
    })


# ─────────────────────────────── activity ───────────────────────────────
@staff_required
def activity_view(request):
    tab = request.GET.get("tab") or "admin"
    q = (request.GET.get("q") or "").strip()
    if tab == "payments":
        qs = WebhookLog.objects.order_by("-received_at")
        if q:
            qs = qs.filter(Q(transaction_id__icontains=q) | Q(status__icontains=q) | Q(gateway__icontains=q))
        if request.GET.get("errors") == "1":
            qs = qs.exclude(error__isnull=True).exclude(error="")
    elif tab == "fraud":
        qs = FraudAlert.objects.select_related("user__user").order_by("-created_at")
        if q:
            qs = qs.filter(Q(user__user__email__icontains=q) | Q(alert_type__icontains=q))
    else:
        tab = "admin"
        qs = AuditLog.objects.select_related("admin__user").order_by("-created_at")
        if q:
            qs = qs.filter(Q(action__icontains=q) | Q(admin__user__email__icontains=q))
    return render(request, "admin/console/activity.html", {"tab": tab, "page": _page(request, qs), "q": q, "qs": _qs_without_page(request)})


# ─────────────────────────────── settings ───────────────────────────────
@staff_required
def settings_view(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "mode":
            mode = request.POST.get("mode")
            if mode not in ("normal", "maintenance"):
                messages.error(request, "Pick a mode.")
            else:
                msg = (request.POST.get("message") or "").strip()[:1000]
                eta = None
                raw = (request.POST.get("eta") or "").strip()
                if raw:
                    from django.utils.dateparse import parse_datetime

                    eta = parse_datetime(raw)
                    if eta and timezone.is_naive(eta):
                        eta = timezone.make_aware(eta)
                MaintenanceMode.objects.create(mode=mode, message=msg, estimated_return_at=eta, activated_by=request.user.profile)
                cache.delete("platform_mode")
                _log(request, f"Set platform mode: {mode}", message=msg)
                messages.success(request, "The shop is closed for maintenance (admins can still use everything)." if mode == "maintenance" else "The shop is open.")
        elif action == "invoices":
            on = bool(request.POST.get("enabled"))
            SystemSetting.objects.update_or_create(key="invoice_generation_enabled", defaults={"value": on})
            _log(request, f"Invoice generation {'on' if on else 'off'}")
            messages.success(request, f"GST invoices are {'on' if on else 'off'}.")
        elif action == "auto_payouts":
            from apps.commerce.payout_gateway import PROVIDERS

            on = bool(request.POST.get("enabled"))
            provider = request.POST.get("provider") if request.POST.get("provider") in PROVIDERS else "cashfree"
            try:
                limit = max(500, min(200000, int(float(request.POST.get("auto_limit") or 10000))))
            except ValueError:
                limit = 10000
            first = bool(request.POST.get("first_needs_approval"))
            if on and not PROVIDERS[provider].configured():
                messages.error(request, f"Add the {PROVIDERS[provider].label} keys in Vercel first (see the list on this card), then switch automatic payouts on.")
                return redirect("admin_settings")
            SystemSetting.objects.update_or_create(key="auto_payouts", defaults={"value": {
                "enabled": on, "provider": provider, "auto_limit": limit, "first_needs_approval": first}})
            _log(request, f"Automatic payouts {'on' if on else 'off'}", provider=provider, auto_limit=limit, first_needs_approval=first)
            messages.success(request, f"Automatic payouts are on through {PROVIDERS[provider].label}." if on else "Automatic payouts are off. Payouts wait for you in Admin → Payouts.")
        elif action == "appearance":
            on = bool(request.POST.get("dark_mode"))
            SystemSetting.objects.update_or_create(key="dark_mode", defaults={"value": {"enabled": on}})
            cache.delete("global_settings_ctx")
            _log(request, f"Dark mode {'on' if on else 'off'}")
            messages.success(request, "Dark mode is on. Visitors get a light/dark switch; it follows their device until they choose."
                             if on else "Dark mode is off. Everyone sees the light theme and the theme switch is hidden.")
        elif action == "ads":
            client = (request.POST.get("client") or "").strip()[:60]
            slot = (request.POST.get("slot") or "").strip()[:40]
            on = bool(request.POST.get("enabled"))
            import re as _re

            if on and not (_re.fullmatch(r"ca-pub-\d{10,20}", client) and slot.isdigit()):
                messages.error(request, "Enter your AdSense publisher ID (ca-pub-…) and a numeric ad unit ID before switching ads on.")
                return redirect("admin_settings")
            SystemSetting.objects.update_or_create(key="ads", defaults={"value": {"enabled": on, "client": client, "slot": slot}})
            cache.delete("global_settings_ctx")
            _log(request, f"Ads {'on' if on else 'off'}", client=client, slot=slot)
            messages.success(request, "Ads are on. They show on shop pages only, never in checkout, library or dashboards." if on else "Ads are off.")
        elif action == "ad_income":
            from django.utils.dateparse import parse_date

            from apps.commerce.ad_revenue_service import distribute_ad_income

            start, end = parse_date(request.POST.get("start") or ""), parse_date(request.POST.get("end") or "")
            if not start or not end or end < start:
                messages.error(request, "Pick the start and end dates of the ad payment period.")
                return redirect("admin_settings")
            try:
                res = distribute_ad_income(request.POST.get("amount") or "0", start, end, request.user.email)
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect("admin_settings")
            except Exception:
                logger.exception("Ad income share failed")
                messages.error(request, "Couldn't share the ad income. Nothing was paid; try again.")
                return redirect("admin_settings")
            _log(request, f"Shared ad income {start}–{end}", amount=request.POST.get("amount"), djs=res["djs"], credited=str(res["credited"]))
            messages.success(request, f"₹{res['credited']} added to {res['djs']} DJ wallet(s) from {res['views']} page views.")
        elif action == "clear_cache":
            try:
                cache.clear()
            except Exception:
                for k in ("platform_mode", "payments_test_mode", "active_gateway_label", "admin_counts"):
                    cache.delete(k)
            _log(request, "Cleared the site cache")
            messages.success(request, "Cache cleared. Pages rebuild on their next visit.")
        return redirect("admin_settings")
    mode = MaintenanceMode.objects.order_by("-created_at").first()
    inv = SystemSetting.objects.filter(key="invoice_generation_enabled").first()
    ads = SystemSetting.objects.filter(key="ads").first()
    dm = SystemSetting.objects.filter(key="dark_mode").first()
    periods = SystemSetting.objects.filter(key="ad_income_periods").first()
    return render(request, "admin/console/settings.html", {
        "mode": mode, "invoices_on": bool(inv.value) if inv else True,
        "ads": (ads.value or {}) if ads else {},
        "payout_cfg": payout_gateway.config(),
        "payout_providers": [(k, v.label, v.configured()) for k, v in payout_gateway.PROVIDERS.items()],
        "site_url": request.build_absolute_uri("/").rstrip("/"),
        "dark_mode_on": bool((dm.value or {}).get("enabled")) if dm and isinstance(dm.value, dict) else False,
        "ad_periods": list(reversed(((periods.value or {}).get("paid") or [])))[:12] if periods else [],
    })


# ─────────────────────────────── exports ───────────────────────────────
def _export_orders(qs):
    rows = list(qs[:50000])
    titles = _titles(rows)
    return _csv_response(
        f"mixmint-orders-{timezone.now():%Y%m%d}.csv",
        ["order", "date", "status", "buyer", "item_type", "item", "dj", "paid", "dj_earnings", "commission", "platform_fee", "gateway", "gateway_order_id", "gateway_payment_id", "downloaded", "revoked"],
        ((p.pk, p.created_at.strftime("%Y-%m-%d %H:%M"), p.status, p.user.user.email, p.content_type,
          titles.get((p.content_type, p.content_id), ""), p.seller.dj_name if p.seller_id else "", p.price_paid, p.dj_earnings, p.commission,
          p.platform_fee, p.payment_gateway, p.gateway_order_id, p.gateway_payment_id, "yes" if p.download_completed else "no",
          "yes" if p.is_revoked else "no") for p in rows),
    )


@staff_required
def export_view(request, what):
    _log(request, f"Exported {what} CSV")
    stamp = f"{timezone.now():%Y%m%d}"
    if what == "orders":
        return _export_orders(_orders_qs(request))
    if what == "users":
        qs = _users_qs(request)
        return _csv_response(f"mixmint-users-{stamp}.csv", ["email", "name", "role", "admin", "joined", "last_login", "verified_email", "frozen", "banned", "pro"],
                             ((u.email, getattr(u.profile, "full_name", ""), getattr(u.profile, "role", ""), "yes" if u.is_staff else "no",
                               u.date_joined.strftime("%Y-%m-%d"), u.last_login.strftime("%Y-%m-%d") if u.last_login else "",
                               "yes" if u.email_verified else "no", "yes" if getattr(u.profile, "is_frozen", False) else "no",
                               "yes" if getattr(u.profile, "is_banned", False) else "no", "yes" if getattr(u.profile, "is_pro_dj", False) else "no")
                              for u in qs.iterator()))
    if what == "payouts":
        qs = Payout.objects.select_related("dj__profile__user").order_by("-created_at")
        return _csv_response(f"mixmint-payouts-{stamp}.csv", ["id", "created", "dj", "email", "amount", "status", "reference", "processed"],
                             ((p.pk, p.created_at.strftime("%Y-%m-%d"), p.dj.dj_name, p.dj.profile.user.email, p.amount, p.status,
                               p.payment_reference or "", p.processed_at.strftime("%Y-%m-%d") if p.processed_at else "") for p in qs.iterator()))
    if what == "djs":
        qs = DJProfile.objects.select_related("profile__user").order_by("dj_name")
        return _csv_response(f"mixmint-djs-{stamp}.csv", ["dj_name", "email", "status", "city", "store", "pro", "joined"],
                             ((d.dj_name, d.profile.user.email, d.status, d.location or "", f"/dj/{d.slug}/", "yes" if d.profile.is_pro_dj else "no",
                               d.created_at.strftime("%Y-%m-%d")) for d in qs.iterator()))
    if what == "waitlist":
        return _csv_response(f"mixmint-waitlist-{stamp}.csv", ["email", "name", "dj", "source", "joined"],
                             ((w.email, w.full_name, "yes" if w.is_dj else "no", w.source, w.created_at.strftime("%Y-%m-%d")) for w in Waitlist.objects.order_by("-created_at").iterator()))
    return redirect("admin_dashboard")
