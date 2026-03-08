from django.urls import path

from .views import (
    toggle_application_fee, list_pending_djs,
    soft_delete_content,
    freeze_account, unfreeze_account,
    manage_ban, toggle_kill_switch, set_maintenance_mode,
    hold_payout, release_payout, escrow_dj_funds,
    revenue_dashboard, high_value_alerts,
    generate_dmca_template,
    manage_ad_floor, toggle_payment_gateway,
    toggle_invoice_generation, investor_report, investor_report_pdf,
    offers_pricing_dashboard, update_platform_settings, save_promotional_offer,
    health_dashboard,
)


urlpatterns = [
    # DJ Management [Spec §3.3]
    path('dj/fee-toggle/', toggle_application_fee, name='admin_fee_toggle'),
    path('dj/pending/', list_pending_djs, name='admin_pending_djs'),

    # Content Moderation [Spec §3.3]
    path('content/delete/', soft_delete_content, name='admin_soft_delete'),

    # Security Controls [Spec §3.3, §11]
    path('security/freeze/', freeze_account, name='admin_freeze'),
    path('security/unfreeze/', unfreeze_account, name='admin_unfreeze'),
    path('security/ban/', manage_ban, name='admin_ban'),
    path('security/kill-switch/', toggle_kill_switch, name='admin_kill_switch'),
    path('security/maintenance/', set_maintenance_mode, name='admin_maintenance'),

    # Payout Management [Spec P2 §9]
    path('payouts/hold/', hold_payout, name='admin_payout_hold'),
    path('payouts/release/', release_payout, name='admin_payout_release'),
    path('payouts/escrow/', escrow_dj_funds, name='admin_escrow'),

    # Analytics [Spec P2 §12]
    path('analytics/revenue/', revenue_dashboard, name='admin_revenue'),
    path('analytics/high-value/', high_value_alerts, name='admin_high_value'),
    path('analytics/investor-report/', investor_report, name='admin_investor_report'),
    path('analytics/investor-report/pdf/', investor_report_pdf, name='admin_investor_report_pdf'),

    # Legal [Spec §9]
    path('legal/dmca-template/', generate_dmca_template, name='admin_dmca'),

    # Platform Config [Spec §3.3, §10]
    path('config/ad-floor/', manage_ad_floor, name='admin_ad_floor'),
    path('config/payment-gateway/', toggle_payment_gateway, name='admin_payment_gateway'),
    path('config/invoice-generation/', toggle_invoice_generation, name='admin_invoice_generation'),
    
    # Offers & Pricing Dashboard (UI & API)
    path('offers-pricing/', offers_pricing_dashboard, name='admin_offers_pricing'),
    path('api/settings/update/', update_platform_settings, name='api_update_settings'),
    path('api/offers/save/', save_promotional_offer, name='api_save_offer'),
    
    # Platform Health [Imp 09]
    path('health/', health_dashboard, name='admin_health'),
]
