"""
Public catalogue + buying without friction:
  /releases/          every release: type tabs, genre chips, search, sort, pages
  /bundles/, /bundles/<id>/   track bundles: buy all at the bundle price or pick songs
  /drops/             limited drops (fixed number of copies)
  /sell/              "Get listed" page for DJs
  /recover/           email yourself a sign-in link to get your downloads back
  /checkout/guest/    start a purchase with just an email (creates the account)
"""

import json
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.core import signing
from django.core.cache import cache
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import escape
from django.views.decorators.http import require_POST

from apps.core.catalog import attach_stock
from apps.core.net import get_client_ip

PAGE = 24
TYPES = [("all", "All"), ("singles", "Singles"), ("albums", "Album packs"), ("bundles", "Bundles"), ("drops", "Limited drops")]
SORTS = [
    ("new", "Newest upload"), ("old", "Oldest upload"), ("popular", "Popular this week"), ("downloads", "Most downloaded"),
    ("price_low", "Price: low to high"), ("price_high", "Price: high to low"), ("title_az", "Title: A to Z"),
    ("title_za", "Title: Z to A"), ("bpm_low", "BPM: low to high"), ("bpm_high", "BPM: high to low"),
]
PRICES = [("free", "Free", 0, 0), ("u50", "Under ₹50", 0.01, 49.99), ("50-99", "₹50–99", 50, 99.99),
          ("100-199", "₹100–199", 100, 199.99), ("200", "₹200 and up", 200, None)]
BPMS = [("slow", "Under 100", None, 99), ("100-120", "100–120", 100, 120), ("121-128", "121–128", 121, 128),
        ("129-140", "129–140", 129, 140), ("fast", "Over 140", 141, None)]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def _live(qs):
    return qs.filter(is_active=True, is_deleted=False, dj__status="approved", dj__profile__store_paused=False)


def releases_view(request, forced_type=None):
    from collections import Counter

    from django.utils import timezone as tz

    from apps.albums.models import AlbumPack
    from apps.commerce.models import Bundle
    from apps.core.genres import GENRE_GROUPS
    from apps.tracks.models import Track

    g = request.GET
    kind = forced_type or g.get("type") or "all"
    if kind not in dict(TYPES):
        kind = "all"
    q = (g.get("q") or "").strip()[:80]
    genre = (g.get("genre") or "").strip()[:60]
    sort = g.get("sort") if g.get("sort") in dict(SORTS) else "new"
    year = int(g["year"]) if (g.get("year") or "").isdigit() and 2000 < int(g["year"]) < 2200 else None
    month = int(g["month"]) if (g.get("month") or "").isdigit() and 1 <= int(g["month"]) <= 12 else None
    price = g.get("price") if g.get("price") in {k for k, *_ in PRICES} else ""
    bpm = g.get("bpm") if g.get("bpm") in {k for k, *_ in BPMS} else ""
    dj_slug = (g.get("dj") or "").strip()[:80]
    verified = g.get("verified") == "1"

    tracks = _live(Track.objects.select_related("dj", "dj__profile"))
    albums = _live(AlbumPack.objects.select_related("dj", "dj__profile"))
    bundles = _live(Bundle.objects.select_related("dj", "dj__profile")).prefetch_related("bundle_tracks__track")
    if q:
        tracks = tracks.filter(Q(title__icontains=q) | Q(dj__dj_name__icontains=q) | Q(genre__icontains=q))
        albums = albums.filter(Q(title__icontains=q) | Q(dj__dj_name__icontains=q))
        bundles = bundles.filter(Q(title__icontains=q) | Q(dj__dj_name__icontains=q))
    if genre:
        tracks = tracks.filter(genre__iexact=genre)
        albums = albums.none()
        bundles = bundles.filter(bundle_tracks__track__genre__iexact=genre).distinct()
    if kind == "drops":
        tracks, albums, bundles = tracks.filter(copies_limit__isnull=False), albums.filter(copies_limit__isnull=False), bundles.none()
    if dj_slug:
        tracks, albums, bundles = tracks.filter(dj__slug=dj_slug), albums.filter(dj__slug=dj_slug), bundles.filter(dj__slug=dj_slug)
    if verified:
        tracks, albums, bundles = tracks.filter(dj__is_verified=True), albums.filter(dj__is_verified=True), bundles.filter(dj__is_verified=True)
    if price:
        _, _, lo, hi = next(p for p in PRICES if p[0] == price)
        rng = Q(price__gte=lo) & (Q(price__lte=hi) if hi is not None else Q())
        tracks, albums, bundles = tracks.filter(rng), albums.filter(rng), bundles.filter(rng)
    if bpm:
        _, _, lo, hi = next(b for b in BPMS if b[0] == bpm)
        f = Q(bpm__isnull=False) & (Q(bpm__gte=lo) if lo is not None else Q()) & (Q(bpm__lte=hi) if hi is not None else Q())
        tracks, albums, bundles = tracks.filter(f), albums.none(), bundles.none()

    pool = []
    if kind in ("all", "singles", "drops"):
        pool += [("track", t) for t in tracks]
    if kind in ("all", "albums", "drops"):
        pool += [("album", a) for a in albums]
    if kind in ("all", "bundles"):
        pool += [("bundle", b) for b in bundles if b.live_tracks()]

    # Upload year / month: counts come from everything else that is filtered, so the menus show what exists.
    local = lambda o: tz.localtime(o.created_at)  # noqa: E731
    year_counts = Counter(local(o).year for _, o in pool)
    month_counts = Counter(local(o).month for _, o in pool if year is None or local(o).year == year)
    items = [(k, o) for k, o in pool if (year is None or local(o).year == year) and (month is None or local(o).month == month)]

    def bpm_key(o):
        return getattr(o, "bpm", None) or 0

    keyf, rev = {
        "new": (lambda kv: kv[1].created_at, True),
        "old": (lambda kv: kv[1].created_at, False),
        "popular": (lambda kv: getattr(kv[1], "sales_last_7_days", 0) or 0, True),
        "downloads": (lambda kv: getattr(kv[1], "download_count", 0) or 0, True),
        "price_low": (lambda kv: kv[1].price, False),
        "price_high": (lambda kv: kv[1].price, True),
        "title_az": (lambda kv: (kv[1].title or "").lower(), False),
        "title_za": (lambda kv: (kv[1].title or "").lower(), True),
        "bpm_low": (lambda kv: (bpm_key(kv[1]) == 0, bpm_key(kv[1])), False),
        "bpm_high": (lambda kv: bpm_key(kv[1]), True),
    }[sort]
    items.sort(key=keyf, reverse=rev)

    page = Paginator(items, PAGE).get_page(g.get("page"))
    attach_stock([o for k, o in page.object_list if k == "track"], "track")
    attach_stock([o for k, o in page.object_list if k == "album"], "album")
    total = page.paginator.count

    # Newest/oldest: show the results under month headings ("October 2026").
    groups = []
    if sort in ("new", "old"):
        for k, o in page.object_list:
            d = local(o)
            label = f"{MONTHS[d.month - 1]} {d.year}"
            if not groups or groups[-1]["label"] != label:
                groups.append({"label": label, "items": []})
            groups[-1]["items"].append((k, o))

    live_genres = Counter((t or "").strip() for t in _live(Track.objects).exclude(genre__isnull=True).exclude(genre="").values_list("genre", flat=True))
    known = {x for _, grp in GENRE_GROUPS for x in grp}
    genre_groups = [(label, [(x, live_genres.get(x, 0)) for x in grp]) for label, grp in GENRE_GROUPS]
    extra = sorted((x for x in live_genres if x and x not in known), key=str.lower)
    if extra:
        genre_groups.append(("Also on MixMint", [(x, live_genres[x]) for x in extra]))
    genres = [x for x, n in sorted(live_genres.items(), key=lambda kv: -kv[1]) if x][:12]

    from apps.accounts.models import DJProfile

    djs = DJProfile.objects.filter(status="approved", profile__store_paused=False).order_by("dj_name").values("slug", "dj_name")

    filtered = bool(q or genre or year or month or price or bpm or dj_slug or verified)
    params = g.copy()
    params.pop("page", None)
    qs = params.urlencode()

    def without(*keys):
        p2 = params.copy()
        for k in keys:
            p2.pop(k, None)
        return "?" + p2.urlencode()

    labels = {k: lab for k, lab, *_ in PRICES}
    blabels = {k: lab for k, lab, *_ in BPMS}
    active = []
    if q:
        active.append((f"“{q}”", without("q")))
    if genre:
        active.append((genre, without("genre")))
    if year:
        active.append((str(year), without("year", "month") if not month else without("year")))
    if month:
        active.append((MONTHS[month - 1], without("month")))
    if price:
        active.append((labels.get(price, price), without("price")))
    if bpm:
        active.append((f"{blabels.get(bpm, bpm)} BPM", without("bpm")))
    if dj_slug:
        name = next((d["dj_name"] for d in djs if d["slug"] == dj_slug), dj_slug)
        active.append((name, without("dj")))
    if verified:
        active.append(("Verified DJs", without("verified")))

    # Browsing everything (no search/filter): open with Netflix-style rows, the full grid follows.
    rows = []
    if not forced_type and kind == "all" and not filtered and sort == "new" and page.number == 1 and total > 8:
        all_tracks = [o for k, o in items if k == "track"]
        all_albums = [o for k, o in items if k == "album"]
        all_bundles = [o for k, o in items if k == "bundle"]

        def row(rid, title, objs, kind_, more="", sub=""):
            objs = list(objs)[:12]
            if objs:
                attach_stock(objs, kind_) if kind_ in ("track", "album") else None
                rows.append({"id": rid, "title": title, "items": objs, "kind": kind_, "more": more, "sub": sub})

        row("new", "New singles", all_tracks, "track", "?type=singles")
        row("popular", "Popular this week", sorted(all_tracks, key=lambda t: t.sales_last_7_days or 0, reverse=True), "track", "?sort=popular")
        row("albums", "Album packs", all_albums, "album", "?type=albums")
        row("drops", "Limited drops", [t for t in all_tracks if t.copies_limit], "track", "/drops/", "Numbered copies. Once they're gone, they're gone.")
        row("bundles", "Bundles", all_bundles, "bundle", "/bundles/")
        for gname, n in Counter((t.genre or "").strip() for t in all_tracks if t.genre).most_common(4):
            if n >= 3:
                row("g-" + gname.lower().replace(" ", "-"), gname, [t for t in all_tracks if (t.genre or "").strip() == gname], "track", f"?genre={gname}")
    ctx = {
        "page": page, "total": total, "kind": kind, "types": TYPES, "q": q, "genre": genre, "genres": genres,
        "genre_groups": genre_groups, "sort": sort, "sorts": SORTS, "forced": forced_type,
        "heading": {"drops": "Limited drops", "bundles": "Bundles"}.get(forced_type or "", "All releases"),
        "rows": rows, "groups": groups, "qs": qs, "filtered": filtered, "active": active,
        "year": year, "month": month, "price": price, "bpm": bpm, "dj": dj_slug, "verified": verified,
        "years": sorted(year_counts.items(), reverse=True),
        "months": [(i, MONTHS[i - 1], month_counts.get(i, 0)) for i in range(1, 13)],
        "prices": [(k, lab) for k, lab, *_ in PRICES], "bpms": [(k, lab) for k, lab, *_ in BPMS], "djs": djs,
        "n_filters": sum(bool(x) for x in (genre, year, month, price, bpm, dj_slug, verified)) + (kind != "all" and not forced_type),
    }
    return render(request, "catalog/releases.html", ctx)


def bundles_view(request):
    return releases_view(request, forced_type="bundles")


def drops_view(request):
    return releases_view(request, forced_type="drops")


def bundle_detail_view(request, pk):
    from apps.commerce.models import Bundle, Purchase

    bundle = get_object_or_404(_live(Bundle.objects.select_related("dj", "dj__profile")), pk=pk)
    tracks = attach_stock(bundle.live_tracks(), "track")
    if not tracks:
        raise Http404
    owned = set()
    if request.user.is_authenticated:
        owned = set(
            Purchase.objects.filter(user=request.user.profile, content_type="track", content_id__in=[t.id for t in tracks],
                                    status="paid", is_revoked=False).values_list("content_id", flat=True)
        )
    return render(request, "catalog/bundle_detail.html", {
        "bundle": bundle, "tracks": tracks, "owned": owned, "list_total": bundle.list_total(),
        "savings": bundle.savings_percent(), "all_owned": len(owned) == len(tracks),
    })


# ───────────────────────────── Bundle checkout ─────────────────────────────
@require_POST
def bundle_checkout(request, pk):
    """One payment for a bundle: the bundle price is split across its tracks (owned tracks are skipped)."""
    from apps.commerce.models import Bundle, Purchase
    from apps.payments.views import _buyer_fee, _create_gateway_order, _gateway_error, _gateway_payload, get_gateway

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Please log in to continue.", "login": True}, status=401)
    profile = request.user.profile
    bundle = get_object_or_404(_live(Bundle.objects.select_related("dj")), pk=pk)
    tracks = bundle.live_tracks()
    if getattr(profile, "dj_profile", None) is not None and profile.dj_profile == bundle.dj:
        return JsonResponse({"error": "You cannot buy your own bundle."}, status=400)
    owned = set(Purchase.objects.filter(user=profile, content_type="track", content_id__in=[t.id for t in tracks],
                                        status="paid", is_revoked=False).values_list("content_id", flat=True))
    list_total = sum((t.price for t in tracks), Decimal("0"))
    todo = [t for t in tracks if t.id not in owned]
    if not todo:
        return JsonResponse({"error": "You already own every track in this bundle."}, status=400)
    from apps.core.catalog import sold_out

    if any(sold_out(t, "track") for t in todo):
        return JsonResponse({"error": "A track in this bundle just sold out."}, status=400)

    bundle_paise = int((Decimal(bundle.price) * 100).to_integral_value())
    # Each track's share of the bundle price, in proportion to its own price.
    shares = [(bundle_paise * int(t.price * 100)) // max(int(list_total * 100), 1) for t in tracks]
    shares[-1] += bundle_paise - sum(shares)
    lines = [(t, s) for t, s in zip(tracks, shares) if t.id not in owned]
    fee_paise = int(_buyer_fee() * 100)
    total = sum(s for _, s in lines) + fee_paise
    if total < 100:
        return JsonResponse({"error": "Amount is too low to pay online."}, status=400)

    internal_id = f"MMB_{uuid.uuid4().hex[:14].upper()}"
    try:
        gateway = get_gateway(None)
    except Exception as exc:
        return _gateway_error(exc)
    with transaction.atomic():
        for idx, (t, amount) in enumerate(lines):
            amt = amount + (fee_paise if idx == 0 else 0)
            Purchase.objects.create(
                user=profile, content_type="track", content_id=t.id, seller=t.dj, gateway_order_id=internal_id,
                payment_gateway=gateway.name, amount_paise=amt, original_price=t.price, price_paid=Decimal(amt) / 100,
                platform_fee=Decimal(fee_paise) / 100 if idx == 0 else Decimal("0.00"),
                checkout_fee=Decimal(fee_paise) / 100 if idx == 0 else Decimal("0.00"),
                final_price=amt, buyer_role=profile.role, status="pending",
            )
        try:
            result, gateway_order_id = _create_gateway_order(
                gateway, total, internal_id, {"user_id": str(request.user.id), "bundle_id": str(bundle.id)}
            )
        except Exception as exc:
            transaction.set_rollback(True)
            return _gateway_error(exc)
        if gateway_order_id != internal_id:
            Purchase.objects.filter(gateway_order_id=internal_id).update(gateway_order_id=gateway_order_id)
    payload = _gateway_payload(result, gateway_order_id, total)
    payload["description"] = bundle.title
    payload["prefill"] = {"email": request.user.email, "name": profile.full_name}
    return JsonResponse(payload)


# ───────────────────────────── Guest checkout + recovery ─────────────────────────────
def _limited(key, n, seconds=3600):
    cache.add(key, 0, timeout=seconds)
    try:
        return cache.incr(key) > n
    except ValueError:
        return False


LINK_SALT = "mixmint.recover"


def _login(request, user):
    from apps.accounts.frontend_views import _bind_session

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    _bind_session(request)


def _send_signin_link(request, user, subject, intro):
    from apps.admin_panel.email_utils import send_email

    token = signing.dumps({"u": str(user.pk), "l": user.last_login.isoformat() if user.last_login else ""}, salt=LINK_SALT)
    url = request.build_absolute_uri(f"/recover/{token}/")
    send_email(
        to_email=user.email,
        subject=subject,
        html_content=(
            f"<p>{escape(intro)}</p>"
            f"<p><a href='{url}' style='display:inline-block;padding:12px 20px;background:#006B4A;color:#fff;"
            f"border-radius:8px;text-decoration:none;font-weight:600'>Open my library</a></p>"
            "<p style='color:#666;font-size:13px'>This link works once and expires in 30 minutes. "
            "If you didn't ask for it, ignore this email.</p>"
        ),
    )


@require_POST
def guest_checkout_start(request):
    """Buy without making an account first: a new email gets an account and is signed in.
    An email that already has an account must log in (or use a sign-in link) — never auto-login."""
    if request.user.is_authenticated:
        return JsonResponse({"ok": True})
    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        return JsonResponse({"error": "Invalid request."}, status=400)
    email = (data.get("email") or "").strip().lower()
    try:
        validate_email(email)
    except Exception:
        return JsonResponse({"error": "Enter a valid email — your download link and invoice go there."}, status=400)
    if _limited(f"guest_checkout_{get_client_ip(request)}", 10):
        return JsonResponse({"error": "Too many attempts. Try again later."}, status=429)
    User = get_user_model()
    existing = User.objects.filter(email__iexact=email).first()
    if existing:
        return JsonResponse({"error": "This email already has a MixMint account. Log in to buy (or use “Email me a sign-in link”).",
                             "exists": True}, status=409)
    try:
        from apps.accounts.validators import validate_email_domain  # disposable-email guard, if present
    except Exception:
        validate_email_domain = None
    if validate_email_domain:
        try:
            validate_email_domain(email)
        except Exception as exc:
            return JsonResponse({"error": getattr(exc, "message", "Please use a real email address.")}, status=400)
    with transaction.atomic():
        user = User.objects.create_user(email=email)
        user.set_unusable_password()
        user.save()
        profile = user.profile
        profile.full_name = email.split("@")[0][:120]
        profile.save(update_fields=["full_name"])
    _login(request, user)
    try:
        _send_signin_link(request, user, "Your MixMint account", "We made you a MixMint account so your downloads stay safe. "
                          "Use this link any time to get back to your library, and set a password in Account settings.")
    except Exception:
        pass
    return JsonResponse({"ok": True, "created": True})


def recover_view(request):
    sent = False
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        if email and not _limited(f"recover_{get_client_ip(request)}", 8):
            user = get_user_model().objects.filter(email__iexact=email, is_active=True).first()
            if user and not user.profile.is_banned:
                try:
                    _send_signin_link(request, user, "Your MixMint downloads", "Here's your link to get back to everything you bought on MixMint.")
                except Exception:
                    pass
        sent = True  # same answer either way: never reveal who has an account
    return render(request, "catalog/recover.html", {"sent": sent})


def recover_link_view(request, token):
    try:
        data = signing.loads(token, salt=LINK_SALT, max_age=30 * 60)
    except signing.BadSignature:
        messages.error(request, "That link has expired or was already used. Ask for a new one.")
        return redirect("recover")
    user = get_user_model().objects.filter(pk=data.get("u"), is_active=True).first()
    stamp = (user.last_login.isoformat() if user and user.last_login else "") if user else None
    if not user or stamp != data.get("l") or user.profile.is_banned:
        messages.error(request, "That link has expired or was already used. Ask for a new one.")
        return redirect("recover")
    _login(request, user)  # updates last_login → link now dead
    messages.success(request, "You're in. Your purchases are below.")
    return redirect("library_page")


# ───────────────────────────── Get listed ─────────────────────────────
def sell_view(request):
    from apps.accounts.models import DJProfile
    from apps.admin_panel.models import PlatformSettings
    from apps.tracks.models import Track

    ps = PlatformSettings.load()
    return render(request, "catalog/sell.html", {
        "fee_enabled": ps.dj_application_fee_enabled, "fee": ps.dj_application_fee,
        "commission": ps.platform_commission_rate,
        "dj_count": DJProfile.objects.filter(status="approved").count(),
        "release_count": _live(Track.objects).count(),
    })


def explore_redirect(request):
    """Old /explore/ links → /releases/ with the same search."""
    from urllib.parse import urlencode

    g = request.GET
    params = {}
    if g.get("q"):
        params["q"] = g["q"]
    if g.get("genre"):
        params["genre"] = g["genre"]
    t = {"track": "singles", "album": "albums", "tracks": "singles", "albums": "albums"}.get(g.get("type", ""))
    if t:
        params["type"] = t
    s = {"latest": "new", "new": "new", "popular": "popular", "price_low": "price_low", "price_high": "price_high"}.get(g.get("sort", ""))
    if s:
        params["sort"] = s
    return redirect("/releases/" + ("?" + urlencode(params) if params else ""), permanent=True)


# ───────────────────────────── Reports & copyright notices ─────────────────────────────
@require_POST
def report_view(request):
    """Anyone can flag a release (spam, bad audio, copyright). Copyright notices alert the admins at once.
    Accepts JSON (the Report dialog) or a normal form post (the copyright page)."""
    from apps.admin_panel.models import ContentReport
    from apps.albums.models import AlbumPack
    from apps.tracks.models import Track

    is_json = (request.content_type or "").startswith("application/json")
    try:
        data = json.loads(request.body or b"{}") if is_json else request.POST
    except ValueError:
        return JsonResponse({"error": "Invalid request."}, status=400)

    def fail(msg, code=400):
        if is_json:
            return JsonResponse({"error": msg}, status=code)
        messages.error(request, msg)
        return redirect(request.META.get("HTTP_REFERER") or "dmca")

    if _limited(f"report_{get_client_ip(request)}", 10):
        return fail("Too many reports from this network. Please try again in an hour.", 429)

    kind = str(data.get("content_type") or "")
    report_type = str(data.get("report_type") or "")
    reason = str(data.get("reason") or "").strip()[:4000]
    item = None
    if kind in ("track", "album") and str(data.get("content_id") or "").isdigit():
        model = Track if kind == "track" else AlbumPack
        item = model.objects.filter(pk=int(data["content_id"]), is_deleted=False).first()
    link = str(data.get("release_url") or "").strip()
    if item is None and link:  # copyright form: find the release from its MixMint link
        import re

        m = re.search(r"/(tracks|albums)/(\d+)", link)
        if m:
            kind = "track" if m.group(1) == "tracks" else "album"
            item = (Track if kind == "track" else AlbumPack).objects.filter(pk=int(m.group(2))).first()
    if item is None:
        return fail("We couldn't find that release. Paste the link to the track or album page on MixMint.")
    if report_type not in dict(ContentReport.REPORT_TYPES):
        return fail("Choose what's wrong.")
    if len(reason) < 10:
        return fail("Tell us a little more (at least a sentence).")

    email = str(data.get("email") or "").strip().lower()[:254]
    if not request.user.is_authenticated:
        try:
            validate_email(email)
        except Exception:
            return fail("Add your email so we can reply.")
    if report_type == "copyright" and not data.get("sworn"):
        return fail("Please confirm the statement about the copyright notice.")
    evidence = str(data.get("evidence_url") or "").strip()[:500]
    if evidence and not evidence.startswith(("http://", "https://")):
        evidence = ""

    ContentReport.objects.create(
        reporter=request.user.profile if request.user.is_authenticated else None,
        reporter_name=str(data.get("name") or "").strip()[:120],
        reporter_email=email or (request.user.email if request.user.is_authenticated else ""),
        evidence_url=evidence, content_type=kind, content_id=item.pk, report_type=report_type, reason=reason,
    )
    done = ("Thanks. We review copyright notices within 24 hours and email you the outcome."
            if report_type == "copyright" else "Thanks for the report. An admin will review it.")
    if is_json:
        return JsonResponse({"ok": True, "message": done})
    messages.success(request, done)
    return redirect("dmca")
