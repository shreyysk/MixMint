from apps.admin_panel.models import PlatformSettings, PromotionalOffer


def payments_test_mode():
    """True when the gateway taking payments right now is on test/sandbox keys (shows the yellow banner)."""
    from django.conf import settings as dj_settings
    from django.core.cache import cache

    cached = cache.get("payments_test_mode")
    if cached is not None:
        return cached
    try:
        from apps.payments.utils import active_gateway_name

        name = active_gateway_name()
    except Exception:
        name = getattr(dj_settings, "DEFAULT_PAYMENT_GATEWAY", "razorpay")
    if name == "phonepe":
        if getattr(dj_settings, "PHONEPE_CLIENT_ID", ""):
            test = (getattr(dj_settings, "PHONEPE_ENV", "sandbox") or "sandbox").lower() != "production"
        else:
            test = "preprod" in (getattr(dj_settings, "PHONEPE_BASE_URL", "") or "")
    else:
        test = bool(getattr(dj_settings, "PAYMENTS_TEST_MODE", False))
    cache.set("payments_test_mode", test, 30)
    return test


def _gateway_label():
    from django.core.cache import cache

    label = cache.get("payment_gateway_label")
    if label is None:
        try:
            from apps.payments.utils import active_gateway_name

            label = "PhonePe" if active_gateway_name() == "phonepe" else "Razorpay"
        except Exception:
            label = "Razorpay"
        cache.set("payment_gateway_label", label, 30)
    return label


def global_settings(request):
    """
    Injects global platform settings and the active promotional offer into all templates.
    [Spec P3 v3]
    """
    from django.conf import settings as dj_settings
    from django.core.cache import cache

    bot = (getattr(dj_settings, "TELEGRAM_BOT_USERNAME", "") or "").lstrip("@")
    test_mode = {
        "payments_test_mode": payments_test_mode(),
        "payment_gateway_label": _gateway_label(),
        "google_login_enabled": getattr(dj_settings, "GOOGLE_LOGIN_ENABLED", False),
        "help_telegram_url": f"https://t.me/{bot}?start=help" if bot else "",
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

        from .models import ContentReport, CopyrightReport, SupportTicket

        return {
            "admin_counts": {
                "reports": ContentReport.objects.filter(status="pending").count() + CopyrightReport.objects.filter(status="pending").count(),
                "djs": DJProfile.objects.filter(status__in=["pending", "pending_review", "pending_payment"]).count(),
                "payouts": Payout.objects.filter(status__in=["pending", "processing"]).count(),
                "refunds": RefundRequest.objects.filter(status="pending").count(),
                "tickets": SupportTicket.objects.filter(status="open").count(),
            }
        }
    except Exception:
        return {"admin_counts": {}}
