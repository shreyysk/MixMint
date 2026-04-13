from django.urls import path
from .views import download_content
from .listener_views import download_history, purchase_history
from .frontend_views import download_page_view

urlpatterns = [
    # Buyer-facing download page with token countdown [Spec §8]
    path('page/<str:token_str>/', download_page_view, name='download_page'),

    # Secure stream proxy [Spec §4]
    path('<str:token_str>/', download_content, name='download_content'),

    # Listener tracking [Spec §3.1]
    path('history/downloads/', download_history, name='download_history'),
    path('history/purchases/', purchase_history, name='purchase_history'),
]
