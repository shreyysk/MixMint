from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TrackViewSet
from .frontend_views import track_detail_view
from .search_views import advanced_search, popular_this_week, new_releases, top_partnered_djs

router = DefaultRouter()
router.register(r'', TrackViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('<int:pk>/', track_detail_view, name='track_detail'),
    # Search & Discovery [Spec §8]
    path('search/', advanced_search, name='advanced_search'),
    path('popular/', popular_this_week, name='popular_this_week'),
    path('new-releases/', new_releases, name='new_releases'),
    path('top-djs/', top_partnered_djs, name='top_djs'),
]
