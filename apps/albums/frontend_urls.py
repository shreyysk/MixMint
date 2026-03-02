from django.urls import path
from .frontend_views import album_detail_view

urlpatterns = [
    path('<int:pk>/', album_detail_view, name='album_detail'),
]
