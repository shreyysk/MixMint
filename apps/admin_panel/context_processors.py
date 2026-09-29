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
