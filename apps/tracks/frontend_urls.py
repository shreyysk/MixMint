from django.urls import path
from .frontend_views import track_detail_view, track_embed_view

urlpatterns = [
    path('<int:pk>/', track_detail_view, name='track_detail'),
    path('embed/<int:pk>/', track_embed_view, name='track_embed'),
]
