from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse

from apps.core.sitemaps import SITEMAPS

def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /api/",
        "Allow: /",
        f"Sitemap: https://{request.get_host()}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': SITEMAPS}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('i18n/', include('django.conf.urls.i18n')),
    
    # API V1
    path('api/v1/accounts/', include('apps.accounts.api_urls')),
    path('api/v1/tracks/', include('apps.tracks.urls')),
    path('api/v1/albums/', include('apps.albums.urls')),
    path('api/v1/commerce/', include('apps.commerce.urls')),
    path('api/v1/payments/', include('apps.payments.urls')),
    path('api/v1/downloads/', include('apps.downloads.urls')),
    path('api/v1/admin/', include('apps.admin_panel.urls')),
    
    # Platform Improvements API
    path('api/v1/platform/', include('apps.core.urls')),
    
    # Public Legal Pages
    path('legal/', include('apps.commerce.legal_urls')),
    
    # Frontend Pages
    path('', include('apps.accounts.frontend_urls')),
    path('tracks/', include('apps.tracks.frontend_urls')),
    path('albums/', include('apps.albums.frontend_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
