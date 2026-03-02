from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API V1
    path('api/v1/accounts/', include('apps.accounts.api_urls')),
    path('api/v1/tracks/', include('apps.tracks.urls')),
    path('api/v1/albums/', include('apps.albums.urls')),
    path('api/v1/commerce/', include('apps.commerce.urls')),
    path('api/v1/payments/', include('apps.payments.urls')),
    path('api/v1/downloads/', include('apps.downloads.urls')),
    path('api/v1/admin/', include('apps.admin_panel.urls')),
    
    # Public Legal Pages
    path('transparency/', include('apps.commerce.legal_urls')),
    
    # Frontend Pages
    path('', include('apps.accounts.frontend_urls')),
    path('tracks/', include('apps.tracks.frontend_urls')),
    path('albums/', include('apps.albums.frontend_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
