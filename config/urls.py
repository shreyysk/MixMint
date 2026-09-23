from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse, JsonResponse
from django.db import connection
from django.core.cache import cache

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from apps.core.sitemaps import SITEMAPS
from apps.core import cron_views


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /api/",
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
    Public health check endpoint for load balancers / Railway.
    Checks DB connectivity and Redis/Celery broker reachability.
    Returns 200 if all healthy, 503 if any dependency is down.
    """
    checks = {}
    overall_healthy = True

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
        overall_healthy = False

    # Check Redis (Celery broker)
    try:
        cache.set("health_check", "ok", 10)
        if cache.get("health_check") == "ok":
            checks["redis"] = "healthy"
        else:
            checks["redis"] = "unhealthy: cache get/set failed"
            overall_healthy = False
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"
        overall_healthy = False

    status_code = 200 if overall_healthy else 503
    return JsonResponse({"status": "healthy" if overall_healthy else "unhealthy", "checks": checks}, status=status_code)


urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="django.contrib.sitemaps.views.sitemap"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path(".well-known/security.txt", security_txt, name="security_txt"),
    path("health/", health_check, name="health_check"),
    path("cron/<str:job>/", cron_views.run_cron_job, name="cron_job"),
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
