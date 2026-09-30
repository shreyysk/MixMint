"""
MixMint Admin Panel API [Spec §3.3, P2 §12].

Admin capabilities:
- DJ management (approve, reject, verify, toggle fee)
- Content moderation (soft delete with notification)
- Security controls (ban, freeze, kill switch, maintenance)
- Payout management (hold, release)
- Revenue analytics dashboard
- DMCA template generation
"""

from apps.core.net import get_client_ip
from django.shortcuts import render
from django.utils.dateparse import parse_datetime
from .models import PlatformSettings, PromotionalOffer
from decimal import Decimal
from django.db.models import Sum, Count
from django.db.models.functions import TruncWeek
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from apps.accounts.models import Profile, DJProfile
from apps.commerce.models import (
    Purchase,
    DJWallet,
    Payout,
    AdRevenueLog,
)
from apps.tracks.models import Track
from apps.albums.models import AlbumPack
from .models import (
    SystemSetting,
    AuditLog,
    BanList,
    KillSwitch,
    MaintenanceMode,
    SupportTicket,
)

# ─── DJ Management ───────────────────────────────────────────────


@api_view(["POST"])
@permission_classes([IsAdminUser])
def toggle_application_fee(request):
    """Enable/disable ₹99 DJ application fee [Spec §3.3]."""
    enabled = request.data.get("enabled", True)
    setting, _ = SystemSetting.objects.update_or_create(
        key="dj_application_fee_enabled",
        defaults={"value": {"enabled": enabled}, "description": "DJ application fee toggle"},
    )
    _log_admin_action(request, f"Set DJ application fee: {'enabled' if enabled else 'disabled'}")
    return Response({"enabled": enabled})


@api_view(["GET"])
@permission_classes([IsAdminUser])
def list_pending_djs(request):
    """List pending DJ applications [Spec §3.3]."""
    pending = DJProfile.objects.filter(status="pending").select_related("profile__user")
    data = []
    for dj in pending:
        try:
            fee_paid = dj.application_fee.status == "paid"
        except Exception:
            fee_paid = False

        data.append(
            {
                "id": dj.id,
                "dj_name": dj.dj_name,
                "email": dj.profile.user.email,
                "fee_paid": fee_paid,
                "created_at": dj.created_at.isoformat(),
            }
        )
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def dj_management_view(request):
    """Admin page: review DJ applications (approve / reject) and manage active sellers."""
    from django.db.models import Count, Q
    from django.shortcuts import render

    groups = {
        "pending": ("pending", "pending_review", "pending_payment"),
        "active": ("approved",),
        "rejected": ("rejected", "banned"),
    }
    qs = (
        DJProfile.objects.select_related("profile__user")
        .annotate(track_count=Count("tracks", filter=Q(tracks__is_deleted=False), distinct=True))
        .order_by("-created_at")
    )
    djs = {key: [] for key in groups}
    for dj in qs:
        key = next((k for k, statuses in groups.items() if dj.status in statuses), None)
        if key is None:
            continue
        wallet = getattr(dj, "wallet", None) if hasattr(dj, "wallet") else None
        fee = getattr(dj, "application_fee", None) if hasattr(dj, "application_fee") else None
        djs[key].append(
            {
                "dj": dj,
                "email": dj.profile.user.email,
                "fee_status": fee.status if fee else None,
                "available": getattr(wallet, "available_for_payout", 0) or 0,
                "total": getattr(wallet, "total_earnings", 0) or 0,
                "is_verified": dj.profile.is_verified_dj,
            }
        )
    tab = request.GET.get("tab") if request.GET.get("tab") in groups else ("pending" if djs["pending"] else "active")
    return render(
        request,
        "admin/dj_management.html",
        {"djs": djs, "tab": tab, "counts": {k: len(v) for k, v in djs.items()}},
    )


@api_view(["POST"])
@permission_classes([IsAdminUser])
def soft_delete_content(request):
    """
    Soft delete track or album with DJ notification [Spec §3.3].
    Archives content metadata before deletion [Spec §9].
    """
    content_id = request.data.get("content_id")
    content_type = request.data.get("content_type", "track")
    reason = request.data.get("reason", "Content removed by admin.")

    if content_type == "track":
        try:
            content = Track.objects.get(id=content_id)
        except Track.DoesNotExist:
            return Response({"error": "Track not found."}, status=status.HTTP_404_NOT_FOUND)
        dj = content.dj
    elif content_type in ("album", "zip"):
        try:
            content = AlbumPack.objects.get(id=content_id)
        except AlbumPack.DoesNotExist:
            return Response({"error": "Album not found."}, status=status.HTTP_404_NOT_FOUND)
        dj = content.dj
    else:
        return Response({"error": "Invalid content_type."}, status=status.HTTP_400_BAD_REQUEST)

    # Archive before delete [Spec §9: Automatic archive of deleted content]
    from .content_archive import archive_content

    archive_content(
        content=content,
        content_type=content_type if content_type != "zip" else "album",
        reason=reason,
        deleted_by=request.user.email,
    )

    # Soft delete [Spec: Soft delete only]
    content.is_deleted = True
    content.is_active = False
    content.save(update_fields=["is_deleted", "is_active"])

    # Notify DJ [Spec §3.3]
    try:
        from apps.admin_panel.email_utils import send_email

        send_email(
            to_email=dj.profile.user.email,
            subject="MixMint: Your content was removed",
            html_content=(
                f"<p>Your content <strong>{content.title}</strong> was removed by MixMint admin moderation.</p>"
                f"<p><strong>Reason:</strong> {reason}</p>"
                f"<p>If you believe this is a mistake, reply to this email for review.</p>"
            ),
        )
    except Exception:
        pass

    # Log admin action
    _log_admin_action(
        request,
        f"Soft deleted {content_type} #{content_id}: {content.title}",
        metadata={"content_id": content_id, "content_type": content_type, "reason": reason},
    )

    return Response(
        {
            "status": "deleted",
            "message": f"{content.title} has been soft-deleted and archived.",
            "archived": True,
            "dj_notified": True,
        }
    )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def moderation_hub_view(request):
    """Premium UI for content moderation [Spec §3.3]."""
    import json
    from django.shortcuts import render
    from django.core.serializers.json import DjangoJSONEncoder

    # Fetch active tracks and albums for moderation
    tracks = (
        Track.objects.filter(is_deleted=False).select_related("dj").values("id", "title", "dj__dj_name", "is_active")
    )
    # Rename dj__dj_name to dj_name for the template
    tracks_list = []
    for t in tracks:
        tracks_list.append(
            {"id": t["id"], "title": t["title"], "dj_name": t["dj__dj_name"], "is_active": t["is_active"]}
        )

    albums = (
        AlbumPack.objects.filter(is_deleted=False)
        .select_related("dj")
        .values("id", "title", "dj__dj_name", "is_active")
    )
    albums_list = []
    for a in albums:
        albums_list.append(
            {"id": a["id"], "title": a["title"], "dj_name": a["dj__dj_name"], "is_active": a["is_active"]}
        )

    ctx = {
        "tracks_json": json.dumps(tracks_list, cls=DjangoJSONEncoder),
        "albums_json": json.dumps(albums_list, cls=DjangoJSONEncoder),
    }
    return render(request, "admin/moderation_hub.html", ctx)


# ─── Security Controls ───────────────────────────────────────────


@api_view(["POST"])
@permission_classes([IsAdminUser])
def freeze_account(request):
    """Freeze a user account [Spec §3.3, §11]."""
    user_id = request.data.get("user_id")
    email = request.data.get("email")
    reason = request.data.get("reason", "Account frozen by admin.")

    try:
        if user_id:
            profile = Profile.objects.get(user_id=user_id)
        elif email:
            profile = Profile.objects.get(user__email=email)
        else:
            return Response({"error": "user_id or email required."}, status=status.HTTP_400_BAD_REQUEST)
    except Profile.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    profile.is_frozen = True
    profile.save(update_fields=["is_frozen"])

    _log_admin_action(request, f"Froze account: {profile.user.email}", metadata={"reason": reason})
    return Response({"status": "frozen", "user": profile.user.email})


@api_view(["POST"])
@permission_classes([IsAdminUser])
def unfreeze_account(request):
    """Unfreeze a user account."""
    user_id = request.data.get("user_id")
    try:
        profile = Profile.objects.get(user_id=user_id)
    except Profile.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    profile.is_frozen = False
    profile.save(update_fields=["is_frozen"])

    _log_admin_action(request, f"Unfroze account: {profile.user.email}")
    return Response({"status": "unfrozen", "user": profile.user.email})


@api_view(["POST"])
@permission_classes([IsAdminUser])
def manage_ban(request):
    """Add/remove IP or device ban [Spec §3.3, §4.6]."""
    action = request.data.get("action", "add")  # 'add' or 'remove'
    ban_type = request.data.get("ban_type")  # 'ip' or 'device'
    value = request.data.get("value")
    reason = request.data.get("reason", "")

    if not ban_type or not value:
        return Response({"error": "ban_type and value required."}, status=status.HTTP_400_BAD_REQUEST)

    if action == "add":
        ban, created = BanList.objects.get_or_create(
            ban_type=ban_type,
            value=value,
            defaults={
                "reason": reason,
                "banned_by": request.user.profile,
                "is_active": True,
            },
        )
        if not created:
            ban.is_active = True
            ban.reason = reason
            ban.save()
        _log_admin_action(request, f"Banned {ban_type}: {value}")
        return Response({"status": "banned", "ban_type": ban_type, "value": value})
    elif action == "remove":
        BanList.objects.filter(ban_type=ban_type, value=value).update(is_active=False)
        _log_admin_action(request, f"Unbanned {ban_type}: {value}")
        return Response({"status": "unbanned", "ban_type": ban_type, "value": value})

    return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def security_dashboard_view(request):
    """Premium UI for security controls [Spec §3.3]."""
    import json
    from django.shortcuts import render
    from django.core.serializers.json import DjangoJSONEncoder

    # Fetch active bans
    active_bans = BanList.objects.filter(is_active=True).values("id", "ban_type", "value", "reason")
    # Map fields for template consistency
    bans_list = []
    for b in active_bans:
        bans_list.append({"id": b["id"], "type": b["ban_type"], "value": b["value"], "reason": b["reason"]})

    ctx = {
        "bans_json": json.dumps(bans_list, cls=DjangoJSONEncoder),
    }
    return render(request, "admin/security_dashboard.html", ctx)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def toggle_kill_switch(request):
    """Activate/deactivate emergency kill switch [Spec §3.3, §4.6]."""
    if "activate" not in request.data:
        return Response({"error": "Pass activate=true or activate=false."}, status=status.HTTP_400_BAD_REQUEST)
    activate = request.data.get("activate")
    if isinstance(activate, str):
        activate = activate.strip().lower() in ("1", "true", "yes", "on")
    reason = request.data.get("reason", "")

    if activate:
        KillSwitch.objects.create(
            is_active=True,
            activated_by=request.user.profile,
            reason=reason,
            activated_at=timezone.now(),
        )
        _log_admin_action(request, "ACTIVATED kill switch", metadata={"reason": reason})
    else:
        KillSwitch.objects.filter(is_active=True).update(
            is_active=False,
            deactivated_at=timezone.now(),
        )
        _log_admin_action(request, "DEACTIVATED kill switch")

    return Response({"kill_switch_active": activate})


@api_view(["POST"])
@permission_classes([IsAdminUser])
def set_maintenance_mode(request):
    """Set platform mode: normal/maintenance/kill_switch [Spec P2 §15]."""
    mode = request.data.get("mode", "normal")
    message = request.data.get("message", "")

    if mode not in ("normal", "maintenance", "kill_switch"):
        return Response({"error": "Invalid mode."}, status=status.HTTP_400_BAD_REQUEST)

    MaintenanceMode.objects.create(
        mode=mode,
        message=message,
        activated_by=request.user.profile,
    )
    from django.core.cache import cache

    cache.delete("platform_mode")
    _log_admin_action(request, f"Set platform mode: {mode}")
    return Response({"mode": mode, "message": message})


# ─── Payout Management ───────────────────────────────────────────


@api_view(["POST"])
@permission_classes([IsAdminUser])
def hold_payout(request):
    """Hold DJ payout for legal review [Spec P2 §9]."""
    dj_id = request.data.get("dj_id")
    reason = request.data.get("reason", "Under review.")

    payouts = Payout.objects.filter(dj_id=dj_id, status="pending")
    count = payouts.update(status="held", hold_reason=reason)

    _log_admin_action(request, f"Held {count} payouts for DJ #{dj_id}", metadata={"reason": reason})
    return Response({"held_count": count, "dj_id": dj_id})


@api_view(["POST"])
@permission_classes([IsAdminUser])
def release_payout(request):
    """Release held payout [Spec P2 §9]."""
    dj_id = request.data.get("dj_id")

    payouts = Payout.objects.filter(dj_id=dj_id, status="held")
    count = payouts.update(status="pending", hold_reason=None)

    _log_admin_action(request, f"Released {count} payouts for DJ #{dj_id}")
    return Response({"released_count": count, "dj_id": dj_id})


@api_view(["POST"])
@permission_classes([IsAdminUser])
def escrow_dj_funds(request):
    """Move withdrawable DJ earnings into escrow under an admin hold [Spec P2 §9]."""
    from decimal import InvalidOperation

    from apps.commerce.escrow_utils import place_earnings_hold

    dj_id = request.data.get("dj_id")
    try:
        amount = Decimal(str(request.data.get("amount", 0)))
    except InvalidOperation:
        return Response({"error": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)
    if amount <= 0:
        return Response({"error": "Amount must be positive."}, status=status.HTTP_400_BAD_REQUEST)
    if not DJWallet.objects.filter(dj_id=dj_id).exists():
        return Response({"error": "DJ wallet not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        place_earnings_hold(
            dj_id,
            "admin_manual",
            amount=amount,
            reason=str(request.data.get("reason", ""))[:500],
            admin_id=request.user.pk,
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    wallet = DJWallet.objects.get(dj_id=dj_id)
    _log_admin_action(request, f"Escrowed ₹{amount} for DJ #{dj_id}")
    return Response({"escrowed": str(amount), "new_escrow_total": str(wallet.escrow_amount)})


# ─── Revenue Analytics ────────────────────────────────────────────


@api_view(["GET"])
@permission_classes([IsAdminUser])
def revenue_dashboard(request):
    """Platform revenue analytics [Spec P2 §12]."""
    from apps.commerce.analytics import get_platform_lifetime_revenue

    # Total platform revenue (Daily cache)
    totals_data = get_platform_lifetime_revenue()

    # Ad revenue totals
    ad_totals = AdRevenueLog.objects.aggregate(
        total_ad_revenue=Sum("ad_impression_value"),
    )

    # Weekly breakdown
    weekly = (
        Purchase.objects.filter(
            status="paid",
            created_at__gte=timezone.now() - timezone.timedelta(weeks=12),
        )
        .annotate(week=TruncWeek("created_at"))
        .values("week")
        .annotate(
            revenue=Sum("price_paid"),
            commission=Sum("commission"),
            count=Count("id"),
        )
        .order_by("week")
    )

    # Pending payouts
    pending_payouts = Payout.objects.filter(status="pending").aggregate(total=Sum("amount"))

    return Response(
        {
            "totals": {
                "total_sales": totals_data["total_sales"],
                "total_commission": totals_data["total_commission"],
                "total_checkout_fees": totals_data["total_checkout_fees"],
                "total_dj_earnings": totals_data.get("total_dj_earnings", "0"),
                "total_ad_revenue": str(ad_totals["total_ad_revenue"] or 0),
                "purchase_count": totals_data.get("purchase_count", 0),
            },
            "weekly_breakdown": list(weekly),
            "pending_payouts": str(pending_payouts["total"] or 0),
        }
    )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def high_value_alerts(request):
    """High-value transaction alerts [Spec P2 §12]."""
    threshold = Decimal(request.query_params.get("threshold", "5000"))

    high_value = (
        Purchase.objects.filter(
            status="paid",
            price_paid__gte=threshold,
        )
        .select_related("user", "seller")
        .order_by("-created_at")[:50]
    )

    return Response(high_value)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def revenue_analytics_view(request):
    """Unified UI for financial analytics [Spec P2 §12]."""
    import json
    from django.shortcuts import render
    from django.core.serializers.json import DjangoJSONEncoder
    from apps.commerce.analytics import get_platform_lifetime_revenue

    # 1. Totals
    totals_data = get_platform_lifetime_revenue()
    ad_totals = AdRevenueLog.objects.aggregate(total_ad_revenue=Sum("ad_impression_value"))
    pending_payouts = Payout.objects.filter(status="pending").aggregate(total=Sum("amount"))

    analytics_data = {
        "totals": {
            "total_sales": str(totals_data["total_sales"]),
            "total_commission": str(totals_data["total_commission"]),
            "total_checkout_fees": str(totals_data["total_checkout_fees"]),
            "total_ad_revenue": str(ad_totals["total_ad_revenue"] or 0),
            "purchase_count": totals_data.get("purchase_count", 0),
        },
        "pending_payouts": str(pending_payouts["total"] or 0),
        "weekly_breakdown": [],
    }

    # 2. Weekly breakdown (12 weeks)
    weekly = (
        Purchase.objects.filter(
            status="paid",
            created_at__gte=timezone.now() - timezone.timedelta(weeks=12),
        )
        .annotate(week=TruncWeek("created_at"))
        .values("week")
        .annotate(revenue=Sum("price_paid"), commission=Sum("commission"))
        .order_by("week")
    )

    for w in weekly:
        analytics_data["weekly_breakdown"].append(
            {"week": w["week"].isoformat(), "revenue": float(w["revenue"]), "commission": float(w["commission"])}
        )

    # 3. High-Value Alerts
    threshold = Decimal("5000")
    high_value = (
        Purchase.objects.filter(status="paid", price_paid__gte=threshold)
        .select_related("user", "seller")
        .order_by("-created_at")[:10]
    )

    alerts_list = []
    for p in high_value:
        alerts_list.append(
            {
                "id": p.id,
                "buyer": p.user.full_name,
                "dj": p.seller.dj_name,
                "amount": str(p.price_paid),
                "created_at": p.created_at.strftime("%d %b, %H:%M"),
            }
        )

    ctx = {
        "analytics_json": json.dumps(analytics_data, cls=DjangoJSONEncoder),
        "alerts_json": json.dumps(alerts_list, cls=DjangoJSONEncoder),
    }
    return render(request, "admin/revenue_analytics.html", ctx)


# ─── DMCA ─────────────────────────────────────────────────────────


@api_view(["POST"])
@permission_classes([IsAdminUser])
def generate_dmca_template(request):
    """Generate DMCA takedown notice [Spec §9]."""
    content_id = request.data.get("content_id")
    content_type = request.data.get("content_type", "track")
    reporter_name = request.data.get("reporter_name", "")
    reporter_email = request.data.get("reporter_email", "")

    if content_type == "track":
        try:
            content = Track.objects.get(id=content_id)
        except Track.DoesNotExist:
            return Response({"error": "Content not found."}, status=status.HTTP_404_NOT_FOUND)
        title = content.title
        dj_name = content.dj.dj_name
    else:
        try:
            content = AlbumPack.objects.get(id=content_id)
        except AlbumPack.DoesNotExist:
            return Response({"error": "Content not found."}, status=status.HTTP_404_NOT_FOUND)
        title = content.title
        dj_name = content.dj.dj_name

    template = f"""DMCA TAKEDOWN NOTICE
=====================

Date: {timezone.now().strftime('%Y-%m-%d')}
Platform: MixMint (mixmint.site)

To Whom It May Concern,

I, {reporter_name}, hereby submit this DMCA takedown notice regarding
the following content hosted on MixMint:

Content Title: {title}
Content Type: {content_type.upper()}
Uploaded By: {dj_name}
Content ID: {content_id}

I have a good faith belief that the use of the copyrighted material
described above is not authorized by the copyright owner, its agent,
or the law.

I declare under penalty of perjury that the information in this
notification is accurate and that I am the copyright owner or
authorized to act on behalf of the copyright owner.

Reporter: {reporter_name}
Email: {reporter_email}

This notice is issued in accordance with the Digital Millennium
Copyright Act (DMCA), 17 U.S.C. § 512.
"""

    return Response({"template": template})


@api_view(["POST"])
@permission_classes([IsAdminUser])
def manage_ad_floor(request):
    """Dynamic ad floor pricing control [Spec §3.3]."""
    floor_price = request.data.get("floor_price")

    if floor_price is None:
        return Response({"error": "floor_price required."}, status=status.HTTP_400_BAD_REQUEST)

    setting, _ = SystemSetting.objects.update_or_create(
        key="ad_floor_pricing",
        defaults={"value": {"floor_price": str(floor_price)}, "description": "Dynamic ad floor base price"},
    )
    _log_admin_action(request, f"Updated ad floor pricing to ₹{floor_price}")
    return Response({"ad_floor_price": str(floor_price)})


@api_view(["POST"])
@permission_classes([IsAdminUser])
def toggle_payment_gateway(request):
    """Admin switch between Razorpay and PhonePe [Spec §10]."""
    gateway = request.data.get("gateway", "razorpay")

    if gateway not in ("razorpay", "phonepe"):
        return Response({"error": "Invalid gateway. Choose razorpay or phonepe."}, status=status.HTTP_400_BAD_REQUEST)

    setting, _ = SystemSetting.objects.update_or_create(
        key="active_payment_gateway",
        defaults={"value": {"gateway": gateway}, "description": "Active payment gateway for the platform"},
    )
    _log_admin_action(request, f"Switched payment gateway to {gateway}")
    return Response({"active_gateway": gateway})


@api_view(["POST"])
@permission_classes([IsAdminUser])
def toggle_invoice_generation(request):
    """Enable or disable automatic invoice generation for purchases."""
    enabled = request.data.get("enabled", True)

    setting, _ = SystemSetting.objects.update_or_create(
        key="invoice_generation_enabled",
        defaults={"value": {"enabled": enabled}, "description": "Toggle automatic invoice generation"},
    )
    _log_admin_action(request, f"{'Enabled' if enabled else 'Disabled'} invoice generation")
    return Response({"invoice_generation_enabled": enabled})


@api_view(["GET"])
@permission_classes([IsAdminUser])
def investor_report(request):
    """
    Visual dashboard for platform transparency [Spec §12].
    Shows GMV, commissions, and ad revenue.
    """
    from django.db.models import Sum
    from apps.commerce.models import Purchase, AdRevenueLog
    from apps.accounts.models import DJProfile
    from django.shortcuts import render

    total_stats = Purchase.objects.filter(status="paid").aggregate(gmv=Sum("price_paid"), comm=Sum("commission"))

    ad_revenue = AdRevenueLog.objects.aggregate(total=Sum("ad_impression_value"))["total"] or 0
    total_djs = DJProfile.objects.count()
    active_djs = DJProfile.objects.filter(status="approved").count()
    pro_djs = DJProfile.objects.filter(profile__is_pro_dj=True).count()

    settings = PlatformSettings.load()
    std_rate = float(settings.platform_commission_rate)

    # Calculate effective avg rate: (pro * 8 + (total-pro)*std_rate) / total
    if total_djs > 0:
        eff_rate = (pro_djs * 8 + (total_djs - pro_djs) * std_rate) / total_djs
    else:
        eff_rate = std_rate

    ctx = {
        "total_gmv": str(total_stats["gmv"] or 0.00),
        "platform_commission": str(total_stats["comm"] or 0.00),
        "ad_revenue": str(ad_revenue),
        "total_dj_count": total_djs,
        "active_djs": active_djs,
        "pro_dj_count": pro_djs,
        "std_commission_rate": std_rate,
        "avg_commission_rate": round(eff_rate, 2),
    }

    return render(request, "admin/investor_dashboard.html", ctx)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def investor_report_pdf(request):
    """
    Export investor dashboard as downloadable PDF [Spec §12].
    Suitable for sharing with investors or stakeholders.
    """
    import io
    from django.http import HttpResponse
    from django.db.models import Sum
    from apps.commerce.models import Purchase, AdRevenueLog
    from apps.accounts.models import DJProfile

    total_stats = Purchase.objects.filter(status="paid").aggregate(
        gmv=Sum("price_paid"),
        comm=Sum("commission"),
        purchase_count=Count("id"),
    )
    ad_revenue = AdRevenueLog.objects.aggregate(total=Sum("ad_impression_value"))["total"] or 0
    settings = PlatformSettings.load()
    std_rate = float(settings.platform_commission_rate)

    # Get DJ counts for effective commission rate calculation
    total_djs = DJProfile.objects.count()
    active_djs = DJProfile.objects.filter(status="approved").count()
    pro_djs = Profile.objects.filter(is_pro_dj=True, role="dj").count()
    eff_rate = (pro_djs * 8 + (total_djs - pro_djs) * std_rate) / total_djs if total_djs > 0 else std_rate

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("title", parent=styles["Heading1"], fontSize=22, spaceAfter=6)
        subtitle_style = ParagraphStyle("subtitle", parent=styles["Normal"], fontSize=10, textColor=colors.grey)

        elements = []

        elements.append(Paragraph("MixMint — Investor Report", title_style))
        elements.append(Paragraph(f"Generated: {timezone.now().strftime('%d %B %Y, %H:%M UTC')}", subtitle_style))
        elements.append(Paragraph("CONFIDENTIAL — For Investor Use Only", subtitle_style))
        elements.append(Spacer(1, 0.8 * cm))

        kpi_data = [
            ["Metric", "Value"],
            ["Gross Merchandise Value (GMV)", f"₹{total_stats['gmv'] or 0}"],
            ["Platform Commission Earned", f"₹{total_stats['comm'] or 0}"],
            ["Ad Revenue (Gross)", f"₹{ad_revenue}"],
            ["Total Purchases", str(total_stats["purchase_count"] or 0)],
            ["Total DJs on Platform", str(total_djs)],
            ["Active (Approved) DJs", str(active_djs)],
            ["Pro DJs (8% commission)", str(pro_djs)],
            ["Effective Commission Rate", f"{round(eff_rate, 2)}%"],
        ]
        kpi_table = Table(kpi_data, colWidths=[10 * cm, 7 * cm])
        kpi_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e91e8c")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 11),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(kpi_table)
        elements.append(Spacer(1, 1 * cm))
        elements.append(
            Paragraph(
                "MixMint is a DJ-first digital music distribution platform operating in India. "
                f"Revenue is generated through track/album sales commissions ({std_rate}% standard, 8% Pro) "
                "and programmatic advertising. All financial data is real-time from the platform database.",
                subtitle_style,
            )
        )

        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()

    except ImportError:
        return HttpResponse("reportlab required. pip install reportlab", status=501, content_type="text/plain")

    response = HttpResponse(pdf, content_type="application/pdf")
    stamp = timezone.now().strftime("%Y%m%d")
    response["Content-Disposition"] = f'attachment; filename="MixMint-Investor-Report-{stamp}.pdf"'
    return response


# ─── Helpers ──────────────────────────────────────────────────────


def _log_admin_action(request, action, target_id=None, metadata=None):
    """Log admin action for audit trail [Spec P2 §12]."""
    AuditLog.objects.create(
        admin=request.user.profile,
        action=action,
        target_id=target_id,
        metadata=metadata or {},
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )


# ─── Offers & Pricing Dashboard ──────────────────────────────────


@api_view(["GET"])
@permission_classes([IsAdminUser])
def offers_pricing_dashboard(request):
    """Render the Offers & Pricing dashboard for admin."""
    settings = PlatformSettings.load()
    offers = PromotionalOffer.objects.all().order_by("-created_at")
    active_offer = offers.filter(is_active=True).first()

    context = {"settings": settings, "offers": offers, "active_offer": active_offer}
    return render(request, "admin/offers_pricing.html", context)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def update_platform_settings(request):
    """Update global platform pricing settings."""
    settings = PlatformSettings.load()

    if "platform_commission_rate" in request.data:
        settings.platform_commission_rate = Decimal(request.data["platform_commission_rate"])
    if "buyer_fee_amount" in request.data:
        settings.buyer_fee_amount = Decimal(request.data["buyer_fee_amount"])
    if "gst_rate" in request.data:
        settings.gst_rate = Decimal(request.data["gst_rate"])
    if "dj_application_fee" in request.data:
        settings.dj_application_fee = Decimal(request.data["dj_application_fee"])
    if "dj_application_fee_enabled" in request.data:
        settings.dj_application_fee_enabled = request.data["dj_application_fee_enabled"]

    settings.save()
    _log_admin_action(request, "Updated Platform Settings (Pricing)")
    return Response({"status": "success", "message": "Settings updated successfully"})


@api_view(["POST"])
@permission_classes([IsAdminUser])
def save_promotional_offer(request):
    """Create or update a promotional offer."""
    data = request.data
    offer_id = data.get("id")

    if offer_id:
        try:
            offer = PromotionalOffer.objects.get(id=offer_id)
        except PromotionalOffer.DoesNotExist:
            return Response({"error": "Offer not found"}, status=404)
    else:
        offer = PromotionalOffer()

    if not (data.get("title") or offer.title):
        return Response({"error": "title is required."}, status=status.HTTP_400_BAD_REQUEST)
    offer.title = str(data.get("title", offer.title))[:255]
    offer.tagline = str(data.get("tagline", getattr(offer, "tagline", "") or data.get("announcement_bar_text", "")))[
        :255
    ]
    offer.badge_label = str(data.get("badge_label", offer.badge_label))[:50]
    offer.sub_text = data.get("sub_text", offer.sub_text)
    if "show_on_navbar" in data:
        offer.show_on_navbar = bool(data["show_on_navbar"])
    if "show_on_track_pages" in data:
        offer.show_on_track_pages = bool(data["show_on_track_pages"])

    if "show_on_homepage" in data:
        offer.show_on_homepage = data["show_on_homepage"]
    if "show_on_checkout" in data:
        offer.show_on_checkout = data["show_on_checkout"]
    if "show_on_dj_upload" in data:
        offer.show_on_dj_upload = data["show_on_dj_upload"]
    if "is_active" in data:
        is_active = data["is_active"]
        if is_active:
            # Deactivate all other offers
            PromotionalOffer.objects.filter(is_active=True, dj__isnull=True).exclude(pk=offer.pk).update(
                is_active=False
            )
        offer.is_active = is_active

    if data.get("starts_at") or data.get("start_date"):
        offer.start_date = parse_datetime(data.get("starts_at") or data.get("start_date"))
    if data.get("ends_at") or data.get("end_date"):
        offer.end_date = parse_datetime(data.get("ends_at") or data.get("end_date"))

    offer.save()
    _log_admin_action(request, f"Saved Promotional Offer: {offer.title}")
    return Response({"status": "success", "offer_id": offer.id})


@api_view(["GET"])
@permission_classes([IsAdminUser])
def health_dashboard(request):
    """Platform health monitoring [Imp 09]."""
    from apps.accounts.models import LoginHistory
    from apps.tracks.models import Track
    from .models import AuditLog, BanList
    from django.shortcuts import render

    # 1. Active Traffic (last 1 hour)
    one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
    active_sessions = LoginHistory.objects.filter(created_at__gte=one_hour_ago).count()

    # 2. Security Alerts (Recent bans & Audit logs)
    recent_bans = BanList.objects.filter(is_active=True).count()
    recent_audits = AuditLog.objects.all().order_by("-created_at")[:10]

    # 3. Content Health
    total_tracks = Track.objects.count()
    deleted_tracks = Track.objects.filter(is_deleted=True).count()

    # 4. Storage / Disk Placeholder
    # Metadata about the environment

    ctx = {
        "active_sessions_1h": active_sessions,
        "security": {
            "active_bans": recent_bans,
            "recent_audits": [
                {"admin": a.admin.user.email, "action": a.action, "time": a.created_at.isoformat()}
                for a in recent_audits
            ],
        },
        "content_health": {
            "total_tracks": total_tracks,
            "deleted_tracks": deleted_tracks,
            "health_percentage": round((1 - (deleted_tracks / total_tracks)) * 100, 1) if total_tracks > 0 else 100,
        },
        "system": {
            "status": "HEALTHY",
            "last_sync": timezone.now().isoformat(),
            "server_region": "ap-south-1",
            "environment": "Production",
        },
    }

    # If HTML requested (for dashboard template)
    if "html" in request.query_params or not request.accepted_renderer.format == "json":
        return render(request, "admin/health.html", ctx)

    return Response(ctx)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_command_center(request):
    """Central hub for all specialized admin dashboards, with today's key numbers."""
    import logging
    from datetime import timedelta

    from apps.accounts.models import User
    from apps.commerce.models import Payout, Purchase, RefundRequest

    from .models import SupportTicket

    logger = logging.getLogger("mixmint")

    since = timezone.now() - timedelta(days=30)
    kpis = {}
    try:
        paid = Purchase.objects.filter(status="paid", is_revoked=False, created_at__gte=since)
        agg = paid.aggregate(gross=Sum("price_paid"), commission=Sum("commission"), fees=Sum("platform_fee"))
        kpis = {
            "users": User.objects.count(),
            "djs": DJProfile.objects.filter(status="approved").count(),
            "pending_djs": DJProfile.objects.filter(status__in=["pending", "pending_review", "pending_payment"]).count(),
            "sales_30d": paid.count(),
            "gross_30d": agg["gross"] or 0,
            "platform_30d": (agg["commission"] or 0) + (agg["fees"] or 0),
            "pending_payouts": Payout.objects.filter(status__in=["pending", "held"]).count(),
            "open_tickets": SupportTicket.objects.filter(status="open").count(),
            "pending_refunds": RefundRequest.objects.filter(status="pending").count(),
        }
    except Exception:
        logger.exception("Admin KPI summary failed")
    return render(request, "admin/admin_dashboard.html", {"kpis": kpis})


@api_view(["GET", "POST"])
@permission_classes([IsAdminUser])
def payouts_admin_view(request):
    """Admin page: send DJ payouts by hand (UPI / bank), then mark them paid with the reference."""
    from django.contrib import messages
    from django.shortcuts import redirect

    if request.method == "POST":
        payout = Payout.objects.filter(pk=request.POST.get("payout_id")).select_related("dj").first()
        action = request.POST.get("action")
        if payout is None:
            messages.error(request, "Payout not found.")
        elif action == "paid" and payout.status in ("pending", "processing", "failed"):
            ref = (request.POST.get("reference") or "").strip()[:255]
            if not ref:
                messages.error(request, "Add the UPI / bank reference number so the DJ can match the payment.")
                return redirect("admin_payouts")
            payout.status, payout.payment_reference, payout.processed_at = "completed", ref, timezone.now()
            payout.save(update_fields=["status", "payment_reference", "processed_at"])
            _log_admin_action(request, f"Marked payout #{payout.id} paid", metadata={"reference": ref})
            messages.success(request, f"Payout #{payout.id} to {payout.dj.dj_name} marked as paid.")
        elif action == "failed" and payout.status in ("pending", "processing"):
            from apps.commerce.models import DJWallet, LedgerEntry
            from django.db import transaction

            with transaction.atomic():
                wallet = DJWallet.objects.select_for_update().get(dj=payout.dj)
                wallet.available_for_payout += payout.amount
                wallet.pending_earnings += payout.amount
                wallet.save(update_fields=["available_for_payout", "pending_earnings", "updated_at"])
                LedgerEntry.objects.create(
                    wallet=wallet, amount=payout.amount, entry_type="credit",
                    description=f"Payout #{payout.id} failed - returned to balance",
                    metadata={"payout_id": payout.id, "type": "payout_reversal"},
                )
                payout.status = "failed"
                payout.hold_reason = (request.POST.get("reason") or "").strip()[:500] or None
                payout.auto_retry_count = 99  # money went back to the balance: never auto-retry this one
                payout.save(update_fields=["status", "hold_reason", "auto_retry_count"])
            _log_admin_action(request, f"Marked payout #{payout.id} failed; money returned to DJ balance")
            messages.success(request, f"Payout #{payout.id} marked failed. The money is back in the DJ's balance.")
        else:
            messages.error(request, "That action isn't possible for this payout.")
        return redirect("admin_payouts")

    open_payouts = Payout.objects.filter(status__in=["pending", "processing", "held"]).select_related("dj__profile__user")
    rows = []
    for p in open_payouts.order_by("created_at"):
        dj = p.dj
        rows.append({"p": p, "dj": dj, "method": (dj.payout_details or {}).get("method") or ("upi" if dj.upi_id else "bank"),
                     "account_name": (dj.payout_details or {}).get("account_name", "")})
    recent = Payout.objects.exclude(status__in=["pending", "processing", "held"]).select_related("dj").order_by("-created_at")[:30]
    return render(request, "admin/payouts.html", {"rows": rows, "recent": recent})


@api_view(["GET", "POST"])
@permission_classes([IsAdminUser])
def refunds_admin_view(request):
    """Admin page: approve (money back via the gateway) or reject buyers' refund requests."""
    from django.contrib import messages
    from django.shortcuts import redirect

    from apps.commerce.models import RefundRequest
    from apps.commerce.views import execute_refund

    if request.method == "POST":
        req = RefundRequest.objects.filter(pk=request.POST.get("refund_id"), status="pending").select_related("purchase").first()
        note = (request.POST.get("note") or "").strip()[:1000]
        if req is None:
            messages.error(request, "That refund request is already handled.")
        elif request.POST.get("action") == "approve":
            if execute_refund(req, note=note or f"Approved by {request.user.email}"):
                _log_admin_action(request, f"Approved refund for purchase #{req.purchase_id}")
                messages.success(request, "Refund sent. The buyer gets the money back in 5–7 working days.")
            else:
                messages.error(request, "The payment gateway refused the refund. Check the Razorpay dashboard, then try again.")
        elif request.POST.get("action") == "reject":
            req.status, req.admin_notes, req.processed_at = "rejected", note or "Rejected", timezone.now()
            req.save(update_fields=["status", "admin_notes", "processed_at"])
            _log_admin_action(request, f"Rejected refund for purchase #{req.purchase_id}")
            messages.success(request, "Refund request rejected.")
        return redirect("admin_refunds")

    pending = RefundRequest.objects.filter(status="pending").select_related("purchase__user__user", "purchase__seller").order_by("created_at")
    rows = []
    for r in pending:
        p = r.purchase
        model = Track if p.content_type == "track" else AlbumPack
        rows.append({"r": r, "p": p, "title": getattr(model.objects.filter(pk=p.content_id).first(), "title", "(deleted)")})
    recent = RefundRequest.objects.exclude(status="pending").select_related("purchase").order_by("-processed_at")[:30]
    return render(request, "admin/refunds.html", {"rows": rows, "recent": recent})


def _vault_ctx():
    from . import vault

    v = vault.status()
    return {"vault": v, "vault_rows": [("Singles channel", v["singles"], v["singles_title"], "singles"),
                                       ("ZIP channel", v["zips"], v["zips_title"], "zips")]}


@api_view(["GET", "POST"])
@permission_classes([IsAdminUser])
def support_admin_view(request):
    """Admin → Support: every question from the Help button, contact page and Telegram bot."""
    from django.conf import settings as dj
    from django.contrib import messages
    from django.shortcuts import redirect

    from . import support

    if request.method == "POST" and request.POST.get("action") == "connect_telegram":
        base = (getattr(dj, "BASE_URL", "") or request.build_absolute_uri("/")).rstrip("/")
        if base.startswith("http://") and "localhost" not in base:
            base = "https://" + base[len("http://"):]
        ok, url = support.set_webhook(base)
        if ok:
            messages.success(request, f"Telegram bot connected. It now delivers messages to {url}.")
        else:
            messages.error(request, "Couldn't connect: check TELEGRAM_BOT_TOKEN in Vercel, then try again.")
        return redirect("admin_support")
    if request.method == "POST" and request.POST.get("action") == "vault_sweep":
        from . import vault

        done = vault.sweep(budget_seconds=200)
        messages.success(request, f"Vault: {done.get('archived', 0)} stored, {done.get('pending', 0)} copying, {done.get('too_large', 0)} R2 only, {done.get('failed', 0)} failed, {done.get('freed', 0)} freed from R2.")
        return redirect("/api/v1/admin/support/#vault")
    if request.method == "POST" and request.POST.get("action") == "vault_settings":
        from .models import PlatformSettings

        ps = PlatformSettings.load()
        try:
            ps.vault_hold_days = min(max(int(request.POST.get("hold_days") or 10), 1), 365)
            ps.vault_rehold_days = min(max(int(request.POST.get("rehold_days") or 3), 1), 90)
        except ValueError:
            messages.error(request, "Days must be whole numbers.")
            return redirect("/api/v1/admin/support/#vault")
        ps.vault_evict_enabled = request.POST.get("evict") == "on"
        ps.save()
        messages.success(request, "Vault settings saved.")
        return redirect("/api/v1/admin/support/#vault")

    status = request.GET.get("status") or "open"
    qs = SupportTicket.objects.select_related("user__user").prefetch_related("messages").order_by("-updated_at")
    if status == "open":
        qs = qs.exclude(status__in=["closed", "resolved"])
    elif status == "closed":
        qs = qs.filter(status__in=["closed", "resolved"])
    info = support.webhook_info() if dj.TELEGRAM_BOT_TOKEN else {}
    return render(
        request,
        "admin/support.html",
        {
            "tickets": qs[:100],
            "status": status,
            "tg_token": bool(dj.TELEGRAM_BOT_TOKEN),
            "tg_chat": bool(dj.TELEGRAM_ADMIN_CHAT_ID),
            "tg_hooked": bool(info.get("url")),
            "tg_error": info.get("last_error_message", ""),
            **_vault_ctx(),
        },
    )


@api_view(["GET", "POST"])
@permission_classes([IsAdminUser])
def support_ticket_admin_view(request, ticket_id):
    from django.contrib import messages
    from django.shortcuts import get_object_or_404, redirect

    from . import support

    ticket = get_object_or_404(SupportTicket.objects.select_related("user__user"), pk=ticket_id)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "reply":
            body = (request.POST.get("body") or "").strip()
            if body:
                where = support.admin_reply(ticket, body, via="web")
                messages.success(request, f"Reply sent by {where}." if where else "Reply saved, but there's no Telegram chat or email to send it to.")
        elif action in ("close", "reopen"):
            ticket.status = "closed" if action == "close" else "open"
            ticket.save(update_fields=["status", "updated_at"])
        return redirect("admin_support_ticket", ticket_id=ticket.id)
    return render(request, "admin/support_ticket.html", {"t": ticket, "thread": ticket.messages.all()})
