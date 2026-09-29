from apps.core.net import get_client_ip
import json

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models.functions import TruncWeek
from django.utils import timezone


def dj_required(json_response=False):
    """Allow only users with a DJ profile; exposes it as request.dj_profile."""
    from functools import wraps

    def deco(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            profile = request.user.profile
            dj = getattr(profile, "dj_profile", None)
            if profile.role != "dj" or dj is None:
                if json_response:
                    return JsonResponse({"error": "DJ account required."}, status=403)
                return redirect("dashboard")
            request.dj_profile = dj
            return view(request, *args, **kwargs)

        return wrapper

    return deco


@login_required
def dashboard_view(request):
    """User dashboard — shows all owned tracks and albums [Spec §3.1, §9]."""
    profile = request.user.profile

    # Fetch all completed purchases
    purchases = profile.purchases.filter(
        status="paid",
    ).order_by("-created_at")

    purchased_tracks = []
    purchased_albums = []

    for purchase in purchases:
        try:
            if purchase.content_type == "track":
                from apps.tracks.models import Track

                content = Track.objects.get(id=purchase.content_id)
                purchased_tracks.append(
                    {
                        "id": purchase.id,
                        "track": content,
                        "purchase_date": purchase.paid_at or purchase.created_at,
                        "can_download": not purchase.is_revoked,
                        "has_insurance": purchase.has_download_insurance,
                    }
                )
            elif purchase.content_type in ("album", "zip"):
                from apps.albums.models import AlbumPack

                content = AlbumPack.objects.get(id=purchase.content_id)
                purchased_albums.append(
                    {
                        "id": purchase.id,
                        "album": content,
                        "purchase_date": purchase.paid_at or purchase.created_at,
                        "can_download": not purchase.is_revoked,
                        "has_insurance": purchase.has_download_insurance,
                    }
                )
        except Exception:
            continue

    wishlist_tracks = profile.wishlist_items.select_related("track", "track__dj")

    wallet = None
    if hasattr(profile, "dj_profile"):
        try:
            wallet = profile.dj_profile.wallet
        except Exception:
            pass

    context = {
        "profile": profile,
        "purchased_tracks": purchased_tracks,
        "purchased_albums": purchased_albums,
        "wishlist_tracks": wishlist_tracks,
        "wallet": wallet,
        "is_dj": profile.role == "dj",
    }
    return render(request, "dashboard/index.html", context)


@login_required
def dj_apply_view(request):
    """View to render the DJ application form."""
    profile = request.user.profile
    if profile.role == "dj":
        return redirect("dj_dashboard")

    # Check if a DJProfile already exists (meaning they already applied)
    try:
        dj_profile = profile.dj_profile
        if dj_profile.status == "pending_payment":
            # They need to pay the application fee
            fee = getattr(dj_profile, "application_fee", None)
            context = {
                "dj_profile": dj_profile,
                "fee_amount": fee.amount if fee else 99.00,
                "status": "pending_payment",
            }
            return render(request, "dashboard/dj_apply_status.html", context)
        elif dj_profile.status == "pending_review" or dj_profile.status == "pending":
            context = {"status": "pending_review"}
            return render(request, "dashboard/dj_apply_status.html", context)
        elif dj_profile.status == "rejected":
            context = {"status": "rejected"}
            return render(request, "dashboard/dj_apply_status.html", context)
    except Exception:
        pass

    if request.method == "POST":
        from .dj_application_views import submit_dj_application

        code, payload = submit_dj_application(request.user, request.POST)
        if code == 201:
            messages.success(request, payload["message"])
            return redirect("apply_as_dj")
        messages.error(request, payload["error"])
        return render(request, "dashboard/dj_apply.html", {"form": request.POST}, status=400)

    return render(request, "dashboard/dj_apply.html")


@login_required
def dj_dashboard_view(request):
    """DJ-specific dashboard with earnings [Spec §3.2]."""
    if request.user.profile.role != "dj" or not hasattr(request.user.profile, "dj_profile"):
        return redirect("dashboard")

    profile = request.user.profile
    try:
        dj_profile = profile.dj_profile
        wallet = dj_profile.wallet
    except Exception:
        wallet = None
        dj_profile = None

    # Calculate Storage Usage
    total_bytes = 0
    forecast = None
    if dj_profile:
        from apps.tracks.models import Track
        from apps.albums.models import AlbumPack
        from django.db.models import Sum
        from apps.commerce.analytics import calculate_earnings_forecast

        track_storage = (
            Track.objects.filter(dj=dj_profile, is_deleted=False).aggregate(total=Sum("file_size"))["total"] or 0
        )
        album_storage = (
            AlbumPack.objects.filter(dj=dj_profile, is_deleted=False).aggregate(total=Sum("file_size"))["total"] or 0
        )
        total_bytes = track_storage + album_storage

        # Calculate earnings forecast [Imp 11]
        try:
            forecast = calculate_earnings_forecast(dj_profile.id)
        except Exception:
            pass

        # Fetch Offload Notifications (Phase 3 Feature 1)
        from apps.commerce.models import OffloadNotification

        offload_notifications = OffloadNotification.objects.filter(dj=dj_profile).order_by("-created_at")

        # Fetch Recent Sales for DJ Dashboard (Phase 3 Feature 2)
        from apps.commerce.models import Purchase

        recent_sales = (
            Purchase.objects.filter(seller=dj_profile, status="paid")
            .select_related("user", "user__dj_profile")
            .order_by("-created_at")[:10]
        )

        # Aggregate Weekly Revenue (Last 12 Weeks) [Imp 11]
        weekly_stats = (
            Purchase.objects.filter(
                seller=dj_profile, status="paid", created_at__gte=timezone.now() - timezone.timedelta(weeks=12)
            )
            .annotate(week=TruncWeek("created_at"))
            .values("week")
            .annotate(revenue=Sum("price_paid"))
            .order_by("week")
        )

        revenue_chart_data = []
        for stat in weekly_stats:
            revenue_chart_data.append({"week": stat["week"].strftime("%d %b"), "revenue": float(stat["revenue"])})
    else:
        offload_notifications = []
        recent_sales = []
        revenue_chart_data = []

    storage_used_mb = total_bytes / (1024 * 1024)
    storage_quota_mb = profile.storage_quota_mb
    storage_percent = (storage_used_mb / storage_quota_mb) * 100 if storage_quota_mb > 0 else 0

    # Calculate total downloads across all DJ tracks
    total_downloads = 0
    if dj_profile:
        total_downloads = (
            Track.objects.filter(dj=dj_profile, is_deleted=False).aggregate(total=Sum("download_count"))["total"] or 0
        )

    total_sales = 0
    active_tracks = []
    if dj_profile:
        from apps.commerce.models import Purchase

        total_sales = Purchase.objects.filter(seller=dj_profile, status="paid", is_revoked=False).count()
        active_tracks = list(Track.objects.filter(dj=dj_profile, is_deleted=False).order_by("-created_at"))

    context = {
        "profile": profile,
        "dj_profile": dj_profile,
        "wallet": wallet,
        "lifetime_earnings": getattr(wallet, "total_earnings", 0) or 0,
        "available_balance": getattr(wallet, "available_for_payout", 0) or 0,
        "escrow_balance": getattr(wallet, "escrow_amount", 0) or 0,
        "total_sales": total_sales,
        "active_tracks": active_tracks,
        "storage_used_mb": round(storage_used_mb, 2),
        "storage_quota_mb": storage_quota_mb,
        "storage_percent": min(round(storage_percent, 1), 100),
        "is_pro": profile.is_pro_dj,
        "forecast": forecast,
        "offload_notifications": offload_notifications,
        "recent_sales": recent_sales,
        "revenue_chart_json": json.dumps(revenue_chart_data),
        "revenue_chart_data": revenue_chart_data,
        "total_downloads": total_downloads,
    }
    return render(request, "dashboard/dj_content.html", context)


@login_required
@require_POST
@dj_required(True)
def add_custom_domain(request):
    """Pro feature: Connect a custom domain [Section C Fix 02]."""
    profile = request.user.profile
    if not profile.is_pro_dj:
        return JsonResponse({"error": "Pro subscription required."}, status=403)

    try:
        data = json.loads(request.body)
        domain = data.get("domain", "").lower().strip()
    except BaseException:
        return JsonResponse({"error": "Invalid request."}, status=400)

    import re as _re

    if (
        not domain
        or len(domain) > 253
        or not _re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", domain)
    ):
        return JsonResponse({"error": "Enter a valid domain like music.yourname.com."}, status=400)
    if any(domain == d or domain.endswith("." + d) for d in ("mixmint.site", "mixmint.in", "vercel.app")):
        return JsonResponse({"error": "That domain can't be used."}, status=400)

    from .models import DJProfile

    dj_profile = request.dj_profile
    if DJProfile.objects.filter(custom_domain=domain).exclude(pk=dj_profile.pk).exists():
        return JsonResponse({"error": "That domain is already connected to another store."}, status=400)

    from .vercel import VercelManager

    try:
        VercelManager().add_domain(domain)
    except Exception:
        import logging

        logging.getLogger("mixmint").exception("Custom domain add failed for %s", domain)
        return JsonResponse({"error": "Couldn't register the domain right now. Try again later."}, status=502)
    dj_profile.custom_domain = domain
    dj_profile.save(update_fields=["custom_domain"])
    return JsonResponse({"status": "success", "message": f"Domain {domain} added. Please update your DNS."})


@login_required
def enable_2fa(request):
    """
    Start TOTP setup for payouts [Fix 06]. The secret is only ever revealed while
    setup is pending; once confirmed it is never shown again (a hijacked session
    must not be able to read the second factor).
    """
    profile = request.user.profile
    dj_profile = getattr(profile, "dj_profile", None)
    if profile.role != "dj" or dj_profile is None:
        return JsonResponse({"error": "DJs only."}, status=403)
    if dj_profile.payout_otp_secret:
        return JsonResponse({"status": "enabled", "message": "Two-factor authentication is already enabled."})

    import pyotp
    from django.core.cache import cache

    cache_key = f"totp_pending_{dj_profile.pk}"
    secret = cache.get(cache_key) or pyotp.random_base32()
    cache.set(cache_key, secret, timeout=900)
    uri = pyotp.TOTP(secret).provisioning_uri(name=request.user.email, issuer_name="MixMint")
    try:
        import segno

        qr = segno.make(uri, error="m").svg_data_uri(scale=4, border=2)
    except Exception:  # QR is a convenience; the secret can still be typed in by hand
        qr = ""
    return JsonResponse({"status": "pending", "totp_uri": uri, "secret": secret, "qr_data_uri": qr})


@login_required
@require_POST
def verify_2fa_setup(request):
    """Confirm the pending secret with a first code, then store it."""
    profile = request.user.profile
    dj_profile = getattr(profile, "dj_profile", None)
    if profile.role != "dj" or dj_profile is None:
        return JsonResponse({"error": "DJs only."}, status=403)
    try:
        code = str(json.loads(request.body or b"{}").get("code", "")).strip()
    except (ValueError, AttributeError):
        return JsonResponse({"error": "Invalid request."}, status=400)

    import pyotp
    from django.core.cache import cache

    secret = cache.get(f"totp_pending_{dj_profile.pk}")
    if dj_profile.payout_otp_secret:
        return JsonResponse({"status": "success", "message": "2FA already enabled."})
    if not secret:
        return JsonResponse({"error": "Setup expired. Start again."}, status=400)
    if not (code.isdigit() and len(code) == 6 and pyotp.TOTP(secret).verify(code, valid_window=1)):
        return JsonResponse({"error": "Invalid verification code."}, status=400)

    dj_profile.payout_otp_secret = secret
    dj_profile.save(update_fields=["payout_otp_secret"])
    cache.delete(f"totp_pending_{dj_profile.pk}")
    return JsonResponse({"status": "success", "message": "2FA successfully enabled."})


@login_required
@dj_required()
def dj_onboarding(request):
    """DJ Onboarding Wizard [Fix 07]."""
    dj_profile = request.dj_profile
    if dj_profile.is_onboarding_complete:
        return redirect("dj_dashboard")

    context = {
        "dj_profile": dj_profile,
        "step": dj_profile.onboarding_step,
    }
    return render(request, "dashboard/dj_onboarding.html", context)


@login_required
@require_POST
@dj_required(True)
def update_onboarding_step(request):
    """Moves the DJ to the next onboarding step."""
    dj_profile = request.dj_profile

    try:
        data = json.loads(request.body)
        step = data.get("step")
    except BaseException:
        return JsonResponse({"error": "Invalid request."}, status=400)

    # Basic step progression
    steps = ["profile_setup", "payout_setup", "first_track", "completed"]
    if step not in steps:
        return JsonResponse({"error": "Invalid step."}, status=400)

    if "bio" in data:
        dj_profile.bio = str(data.get("bio") or "").strip()[:2000]
    if "location" in data:
        dj_profile.location = str(data.get("location") or "").strip()[:255] or None
    dj_profile.onboarding_step = step
    if step == "completed":
        dj_profile.is_onboarding_complete = True
    dj_profile.save()

    return JsonResponse({"status": "success", "next_step": step})


@login_required
def export_user_data(request):
    """GDPR-compliant data export [Imp 02]."""
    profile = request.user.profile

    data = {
        "profile": {
            "email": profile.user.email,
            "full_name": profile.full_name,
            "role": profile.role,
            "is_pro": profile.is_pro_dj,
            "joined_at": profile.created_at.isoformat(),
        },
        "purchases": [
            {
                "id": p.id,
                "content_type": p.content_type,
                "content_id": p.content_id,
                "price_paid": str(p.price_paid),
                "date": p.created_at.isoformat(),
            }
            for p in profile.purchases.all()
        ],
        "ratings": [
            {
                "content_type": r.content_type,
                "content_id": r.content_id,
                "stars": r.stars,
                "review": r.review,
                "date": r.created_at.isoformat(),
            }
            for r in profile.ratings_given.all()
        ],
        "disputes": [
            {"id": d.id, "reason": d.reason, "status": d.status, "date": d.created_at.isoformat()}
            for d in profile.disputes_opened.all()
        ],
    }

    response = JsonResponse(data, json_dumps_params={"indent": 2})
    response["Content-Disposition"] = 'attachment; filename="mixmint_data_export.json"'
    return response


@login_required
@require_POST
def request_account_deletion(request):
    """Soft-delete account and mark for permanent deletion [Imp 02]."""
    profile = request.user.profile
    profile.is_banned = True  # Prevent login
    profile.store_paused = True
    profile.save()

    # Log the request for admin
    from apps.admin_panel.models import AuditLog

    AuditLog.objects.create(
        admin=None,  # User-initiated
        action=f"User {request.user.email} requested account deletion.",
        ip_address=get_client_ip(request),
    )

    return JsonResponse(
        {"status": "success", "message": "Account deletion requested. Your account will be removed within 30 days."}
    )


@login_required
def active_sessions(request):
    """List active user sessions [Imp 05]."""
    from django.contrib.sessions.models import Session
    from django.utils import timezone

    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    user_sessions = []

    for session in sessions:
        decoded = session.get_decoded()
        if decoded.get("_auth_user_id") == str(request.user.id):
            user_sessions.append(
                {
                    "session_key": session.session_key,
                    "expire_date": session.expire_date.isoformat(),
                    "is_current": session.session_key == request.session.session_key,
                }
            )

    return render(request, "dashboard/sessions.html", {"sessions": user_sessions})


@login_required
@require_POST
def logout_device(request):
    """Terminate a specific session [Imp 05]."""
    session_key = json.loads(request.body).get("session_key")
    from django.contrib.sessions.models import Session

    try:
        session = Session.objects.get(session_key=session_key)
        if session.get_decoded().get("_auth_user_id") == str(request.user.id):
            session.delete()
            return JsonResponse({"status": "success"})
    except BaseException:
        pass

    return JsonResponse({"status": "error", "message": "Session not found."}, status=404)


@login_required
@dj_required(True)
def check_custom_domain_status(request):
    """Check DNS and SSL status via Vercel API."""
    dj_profile = request.dj_profile
    domain = dj_profile.custom_domain

    if not domain:
        return JsonResponse({"error": "No custom domain configured."}, status=404)

    from .vercel import VercelManager

    vm = VercelManager()
    status = vm.get_domain_status(domain)

    if status:
        return JsonResponse({"status": "success", "data": status})
    return JsonResponse({"error": "Could not fetch status."}, status=500)


@login_required
@dj_required()
def bundle_management_view(request):
    """Imp 12: View and manage track bundles."""
    if request.user.profile.role != "dj" or not hasattr(request.user.profile, "dj_profile"):
        return redirect("dashboard")

    dj_profile = request.dj_profile
    bundles = dj_profile.bundles.filter(is_deleted=False).prefetch_related("bundle_tracks__track")
    tracks = dj_profile.tracks.filter(is_deleted=False, is_active=True)

    context = {
        "bundles": bundles,
        "tracks": tracks,
    }
    return render(request, "dashboard/bundles.html", context)


@login_required
@require_POST
@dj_required()
def create_bundle_view(request):
    """Create a new discounted track bundle."""
    from apps.commerce.models import Bundle, BundleTrack

    dj_profile = request.dj_profile

    title = request.POST.get("title")
    price = request.POST.get("price")
    selected_tracks = request.POST.getlist("tracks")  # track IDs

    from decimal import Decimal, InvalidOperation
    from django.contrib import messages

    try:
        price = Decimal(str(price)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        price = None
    title = (title or "").strip()[:200]
    # Only the DJ's own live tracks can go into their bundle.
    own_tracks = list(
        dj_profile.tracks.filter(id__in=[t for t in selected_tracks if str(t).isdigit()], is_deleted=False)
    )
    if not title or price is None or price <= 0 or len(own_tracks) < 2:
        messages.error(request, "A bundle needs a title, a positive price and at least 2 of your tracks.")
        return redirect("bundle_management")

    bundle = Bundle.objects.create(dj=dj_profile, title=title, price=price)
    for order, track in enumerate(own_tracks):
        BundleTrack.objects.create(bundle=bundle, track=track, display_order=order)
    messages.success(request, "Bundle created.")
    return redirect("bundle_management")


@login_required
@require_POST
@dj_required()
def delete_bundle_view(request, bundle_id):
    """Soft-delete one of the DJ's own bundles (past buyers keep what they bought)."""
    from django.contrib import messages

    updated = request.dj_profile.bundles.filter(id=bundle_id, is_deleted=False).update(is_deleted=True)
    if updated:
        messages.success(request, "Bundle deleted.")
    else:
        messages.error(request, "Bundle not found.")
    return redirect("bundle_management")


@login_required
@dj_required()
def announcement_management_view(request):
    """Imp 14: View and manage DJ announcements."""
    if request.user.profile.role != "dj" or not hasattr(request.user.profile, "dj_profile"):
        return redirect("dashboard")

    dj_profile = request.dj_profile
    announcements = dj_profile.announcements.all()

    return render(request, "dashboard/announcements.html", {"announcements": announcements})


@login_required
@require_POST
@dj_required()
def create_announcement_view(request):
    """Post a new update to the storefront."""
    from .models import DJAnnouncement

    dj_profile = request.dj_profile

    title = request.POST.get("title")
    content = request.POST.get("content")

    title, content = (title or "").strip()[:200], (content or "").strip()[:5000]
    if title and content:
        DJAnnouncement.objects.create(dj=dj_profile, title=title, content=content)

    return redirect("announcement_management")


@login_required
@require_POST
@dj_required()
def delete_announcement_view(request, post_id):
    """Delete an announcement."""
    dj_profile = request.dj_profile
    try:
        announcement = dj_profile.announcements.get(id=post_id)
        announcement.delete()
    except BaseException:
        pass
    return redirect("announcement_management")


@login_required
@dj_required()
def ambassador_management_view(request):
    """Imp 15: DJ Ambassador Program management."""
    if request.user.profile.role != "dj" or not hasattr(request.user.profile, "dj_profile"):
        return redirect("dashboard")

    dj_profile = request.dj_profile
    ambassador = getattr(dj_profile, "ambassador_code", None)

    # Standard profile fields are: user, referred_by, etc.
    # The error 'profile' might have come from a typo or misconfiguration.
    # We use select_related('user') to get the User model data.
    referrals = dj_profile.referrals.select_related("user").order_by("-created_at")[:20]

    context = {
        "ambassador": ambassador,
        "referrals": referrals,
        "referral_url": f"{request.build_absolute_uri('/')}?ref={ambassador.code}" if ambassador else None,
    }
    return render(request, "dashboard/ambassador.html", context)


@login_required
@require_POST
@dj_required()
def generate_ambassador_code_view(request):
    """Generate a unique referral code for the DJ."""
    from .models import AmbassadorCode
    import random
    import string

    dj_profile = request.dj_profile
    if hasattr(dj_profile, "ambassador_code"):
        return redirect("ambassador_management")

    # Generate unique 8-char code
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    while AmbassadorCode.objects.filter(code=code).exists():
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

    AmbassadorCode.objects.create(dj=dj_profile, code=code)
    return redirect("ambassador_management")
