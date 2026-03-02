from .dmca_views import generate_dmca_template
from .views import (
    toggle_application_fee, list_pending_djs,
    soft_delete_content,
    freeze_account, unfreeze_account,
    manage_ban, toggle_kill_switch, set_maintenance_mode,
    hold_payout, release_payout, escrow_dj_funds,
    revenue_dashboard, high_value_alerts,
    generate_dmca_template,
    manage_ad_floor, toggle_payment_gateway,
    toggle_invoice_generation, investor_report,
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

    # Legal [Spec §9]
    path('legal/dmca-template/', generate_dmca_template, name='admin_dmca'),

    # Platform Config [Spec §3.3, §10]
    path('config/ad-floor/', manage_ad_floor, name='admin_ad_floor'),
    path('config/payment-gateway/', toggle_payment_gateway, name='admin_payment_gateway'),
    path('config/invoice-generation/', toggle_invoice_generation, name='admin_invoice_generation'),
]
