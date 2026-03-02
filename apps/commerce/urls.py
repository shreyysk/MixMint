from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PurchaseViewSet, DJWalletViewSet, request_manual_payout, my_library
from .insurance_views import check_insurance_eligibility, purchase_insurance, verify_insurance_payment
from .views_verify import verify_purchase_view
from .legal_views import download_invoice, dj_gst_export
from .dj_analytics import (
    dj_earnings_overview, dj_earnings_per_track,
    dj_earnings_per_album, dj_payout_history
)

router = DefaultRouter()
router.register(r'purchases', PurchaseViewSet, basename='purchase')
router.register(r'wallets', DJWalletViewSet, basename='wallet')

urlpatterns = [
    path('', include(router.urls)),
    path('verify-purchase/', verify_purchase_view, name='verify_purchase'),
    path('payouts/request/', request_manual_payout, name='dj_payout_request'),

    # Download Insurance [Spec §4.3]
    path('insurance/<int:purchase_id>/check/', check_insurance_eligibility, name='check_insurance'),
    path('insurance/<int:purchase_id>/buy/', purchase_insurance, name='buy_insurance'),
    path('insurance/verify/', verify_insurance_payment, name='verify_insurance'),

    # User Library [Spec §3.1]
    path('my-library/', my_library, name='my_library'),

    # Legal & Compliance [Spec §9]
    path('invoice/<int:invoice_id>/', download_invoice, name='download_invoice'),
    path('gst-export/', dj_gst_export, name='dj_gst_export'),

    # DJ Analytics [Spec §3.2]
    path('analytics/overview/', dj_earnings_overview, name='dj_earnings_overview'),
    path('analytics/tracks/', dj_earnings_per_track, name='dj_earnings_per_track'),
    path('analytics/albums/', dj_earnings_per_album, name='dj_earnings_per_album'),
    path('analytics/payouts/', dj_payout_history, name='dj_payout_history'),
]
