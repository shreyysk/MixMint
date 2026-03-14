from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    my_library, pro_landing, activate_pro_trial, request_refund,
    open_dispute, toggle_wishlist, PurchaseViewSet, DJWalletViewSet, request_manual_payout, CartViewSet
)
from .insurance_views import check_insurance_eligibility, purchase_insurance, verify_insurance_payment
from .views_verify import verify_purchase_view
from .legal_views import download_invoice, dj_gst_export
from .dj_analytics import (
    dj_earnings_overview, dj_earnings_per_track,
    dj_earnings_per_album, dj_payout_history, dj_weekly_chart,
)
from .dj_conversion_views import (
    get_referral_code, apply_referral_code, apply_promo_code,
    get_milestones, get_onboarding_status, get_dj_dashboard_stats,
)

router = DefaultRouter()
router.register(r'purchases', PurchaseViewSet, basename='purchase')
router.register(r'wallets', DJWalletViewSet, basename='wallet')
router.register(r'cart', CartViewSet, basename='cart')

urlpatterns = [
    path('', include(router.urls)),
    path('pro/', pro_landing, name='pro_landing'),
    path('pro/activate/', activate_pro_trial, name='activate_pro_trial'),
    path('refund/request/', request_refund, name='request_refund'),
    path('dispute/open/', open_dispute, name='open_dispute'),
    path('wishlist/toggle/', toggle_wishlist, name='toggle_wishlist'),
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

    # DJ Analytics — Revenue Only [Spec §3.2]
    path('analytics/overview/', dj_earnings_overview, name='dj_earnings_overview'),
    path('analytics/tracks/', dj_earnings_per_track, name='dj_earnings_per_track'),
    path('analytics/albums/', dj_earnings_per_album, name='dj_earnings_per_album'),
    path('analytics/payouts/', dj_payout_history, name='dj_payout_history'),
    path('analytics/chart/', dj_weekly_chart, name='dj_weekly_chart'),
    
    # DJ Conversion & Growth [High Conversion Enhancement]
    path('dj/referral/', get_referral_code, name='dj_referral_code'),
    path('dj/referral/apply/', apply_referral_code, name='apply_referral'),
    path('dj/promo/apply/', apply_promo_code, name='apply_promo'),
    path('dj/milestones/', get_milestones, name='dj_milestones'),
    path('dj/onboarding/', get_onboarding_status, name='dj_onboarding'),
    path('dj/dashboard-stats/', get_dj_dashboard_stats, name='dj_dashboard_stats'),
]
