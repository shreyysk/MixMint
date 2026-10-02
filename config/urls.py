from django.contrib import admin
from apps.commerce import payout_webhooks  # noqa: E402
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse, JsonResponse
from django.db import connection
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from apps.core.sitemaps import SITEMAPS
from apps.core import catalog_views, cron_views, support_views
from apps.payments import views as payment_views
from apps.payments.webhooks import phonepe_webhook
from django.views.generic import RedirectView


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /api/",
        "Disallow: /dashboard/",
        "Disallow: /cron/",
        "Allow: /",
        f"Sitemap: https://{request.get_host()}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def security_txt(request):
    lines = [
        "Contact: mailto:security@mixmint.site",
        "Contact: https://t.me/mixmint_support_bot",
        "Policy: https://mixmint.site/legal/security/",
        "Preferred-Languages: en, hi",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def health_check(request):
    """
    Public health check for load balancers. Reports DB + cache without leaking
    error details (those go to the log).
    """
    import logging

    log = logging.getLogger("mixmint")
    checks = {}
    overall_healthy = True

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception:
        log.exception("Health check: database unreachable")
        checks["database"] = "unhealthy"
        overall_healthy = False

    backend = settings.CACHES["default"]["BACKEND"].rsplit(".", 1)[-1]
    try:
        cache.set("health_check", "ok", 10)
        ok = cache.get("health_check") == "ok"
    except Exception:
        log.exception("Health check: cache unreachable")
        ok = False
    checks["cache"] = f"{'healthy' if ok else 'unhealthy'} ({backend})"
    overall_healthy = overall_healthy and ok

    status_code = 200 if overall_healthy else 503
    return JsonResponse({"status": "healthy" if overall_healthy else "unhealthy", "checks": checks}, status=status_code)


@csrf_exempt
def csp_report(request):
    """Collects browser CSP violation reports (logged, never stored)."""
    import logging

    if request.method == "POST":
        logging.getLogger("mixmint.csp").warning("CSP violation: %s", request.body[:2000])
    return HttpResponse(status=204)


urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="django.contrib.sitemaps.views.sitemap"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path(".well-known/security.txt", security_txt, name="security_txt"),
    path("health/", health_check, name="health_check"),
    path("csp-report/", csp_report, name="csp_report"),
    # Payment return/notification aliases for orders created before the URL fix.
    path("payment/callback/", payment_views.payment_callback),
    path("payment/webhook/phonepe/", phonepe_webhook),
    path("payouts/webhook/cashfree/", payout_webhooks.cashfree_payout_webhook, name="cashfree_payout_webhook"),
    path("payouts/webhook/razorpayx/", payout_webhooks.razorpayx_payout_webhook, name="razorpayx_payout_webhook"),
    path("payment/webhook/phonepe/refund/", phonepe_webhook),
    path("checkout/", RedirectView.as_view(url="/cart/", permanent=False)),
    path("cron/<str:job>/", cron_views.run_cron_job, name="cron_job"),
    path("telegram/webhook/", support_views.telegram_webhook, name="telegram_webhook"),
    path("vault/callback/", support_views.vault_callback, name="vault_callback"),
    path("vault/run/", support_views.vault_run, name="vault_run"),
    # Catalogue, guest checkout, download recovery, "get listed"
    path("releases/", catalog_views.releases_view, name="releases"),
    path("bundles/", catalog_views.bundles_view, name="bundles"),
    path("bundles/<int:pk>/", catalog_views.bundle_detail_view, name="bundle_detail"),
    path("bundles/<int:pk>/checkout/", catalog_views.bundle_checkout, name="bundle_checkout"),
    path("drops/", catalog_views.drops_view, name="drops"),
    path("sell/", catalog_views.sell_view, name="sell"),
    path("recover/", catalog_views.recover_view, name="recover"),
    path("report/", catalog_views.report_view, name="report_content"),
    path("recover/<str:token>/", catalog_views.recover_link_view, name="recover_link"),
    path("checkout/guest/", catalog_views.guest_checkout_start, name="guest_checkout"),
    # API Schema & Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # API V1
    path("api/v1/accounts/", include("apps.accounts.api_urls")),
    path("api/v1/tracks/", include("apps.tracks.urls")),
    path("api/v1/albums/", include("apps.albums.urls")),
    path("api/v1/commerce/", include("apps.commerce.urls")),
    path("api/v1/payments/", include("apps.payments.urls")),
    path("api/v1/downloads/", include("apps.downloads.urls")),
    path("api/v1/admin/", include("apps.admin_panel.urls")),
    # Platform Improvements API
    path("api/v1/platform/", include("apps.core.urls")),
    # Public Legal Pages
    path("legal/", include("apps.commerce.legal_urls")),
    # Frontend Pages
    path("", include("apps.accounts.frontend_urls")),
    path("tracks/", include("apps.tracks.frontend_urls")),
    path("albums/", include("apps.albums.frontend_urls")),
    path("social-auth/", include("social_django.urls", namespace="social")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
