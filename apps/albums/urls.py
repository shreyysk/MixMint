from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AlbumPackViewSet
from .frontend_views import album_detail_view

router = DefaultRouter()
router.register(r'', AlbumPackViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('<int:pk>/', album_detail_view, name='album_detail'),
]
