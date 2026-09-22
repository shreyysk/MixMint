from django.urls import path
from .asset_views import asset_handbook_pdf, asset_pack_view
from .frontend_views import track_detail_view, track_embed_view

urlpatterns = [
    path("asset-pack/", asset_pack_view, name="dj_asset_pack"),
    path("asset-pack/handbook.pdf", asset_handbook_pdf, name="dj_asset_handbook"),
    path("<int:pk>/", track_detail_view, name="track_detail"),
    path("embed/<int:pk>/", track_embed_view, name="track_embed"),
]
