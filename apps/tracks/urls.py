from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TrackViewSet
from .frontend_views import track_detail_view
from .search_views import advanced_search, popular_this_week, new_releases, top_partnered_djs
from .collab_views import invite_collaborator, remove_collaborator, list_collaborators

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
    # Collaboration Invite Engine [Spec P2 §4]
    path('<int:track_id>/collabs/', list_collaborators, name='track_collabs_list'),
    path('<int:track_id>/collabs/invite/', invite_collaborator, name='track_collab_invite'),
    path('<int:track_id>/collabs/<int:collab_dj_id>/', remove_collaborator, name='track_collab_remove'),
]
