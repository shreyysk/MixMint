from apps.admin_panel.models import PlatformSettings, PromotionalOffer


def global_settings(request):
    """
    Injects global platform settings and the active promotional offer into all templates.
    [Spec P3 v3]
    """
    from django.conf import settings as dj_settings
    from django.core.cache import cache

    test_mode = {
        "payments_test_mode": getattr(dj_settings, "PAYMENTS_TEST_MODE", False),
        "google_login_enabled": getattr(dj_settings, "GOOGLE_LOGIN_ENABLED", False),
    }
    cached = cache.get("global_settings_ctx")
    if cached is not None:
        return {**cached, **test_mode}
    settings = PlatformSettings.load()
    # Site-wide banner = platform offers only; DJ-owned offers show on that DJ's pages.
    active_offer = PromotionalOffer.objects.filter(is_active=True, dj__isnull=True).first()
    try:
        dj_share = max(0, 100 - float(settings.platform_commission_rate))
        dj_share = int(dj_share) if dj_share == int(dj_share) else round(dj_share, 1)
    except (TypeError, ValueError):
        dj_share = None
    ctx = {"platform_settings": settings, "active_promotional_offer": active_offer, "dj_share_percent": dj_share}
    cache.set("global_settings_ctx", ctx, 30)
    return {**ctx, **test_mode}


def admin_nav(request):
    """Badge counts for the admin sidebar (only computed on admin pages)."""
    path = getattr(request, "path", "") or ""
    user = getattr(request, "user", None)
    if not (path.startswith("/api/v1/admin/") and user is not None and user.is_authenticated and user.is_staff):
        return {}
    try:
        from apps.accounts.models import DJProfile
        from apps.commerce.models import Payout, RefundRequest

        from .models import SupportTicket

        return {
            "admin_counts": {
                "djs": DJProfile.objects.filter(status__in=["pending", "pending_review", "pending_payment"]).count(),
                "payouts": Payout.objects.filter(status__in=["pending", "processing"]).count(),
                "refunds": RefundRequest.objects.filter(status="pending").count(),
                "tickets": SupportTicket.objects.exclude(status__in=["resolved", "closed"]).count(),
            }
        }
    except Exception:
        return {"admin_counts": {}}
