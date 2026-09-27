from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AlbumPackViewSet

router = DefaultRouter()
router.register(r"", AlbumPackViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
