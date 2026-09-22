from django.urls import path
from .views import download_content
from .external_views import download_external, issue_external_token
from .listener_views import download_history, purchase_history
from .frontend_views import download_page_view

urlpatterns = [
    # Buyer-facing download page with token countdown [Spec §8]
    path("page/<str:token_str>/", download_page_view, name="download_page"),
    # External-source flow: mint token, then stream via MixMint endpoint only
    path("external/issue/", issue_external_token, name="external_issue_token"),
    path("external/<str:token_str>/", download_external, name="download_external"),
    # Secure stream proxy [Spec §4]
    path("<str:token_str>/", download_content, name="download_content"),
    # Listener tracking [Spec §3.1]
    path("history/downloads/", download_history, name="download_history"),
    path("history/purchases/", purchase_history, name="purchase_history"),
]
