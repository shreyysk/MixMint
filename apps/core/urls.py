from django.urls import path
from .improvements import (
    # DJ Experience
    dj_quick_stats, quick_upload_track,
    # Buyer Experience
    smart_search, homepage_feed, quick_checkout,
    # Admin Tools
    admin_dashboard_stats, pending_dj_approvals, quick_approve_dj, flagged_content,
)
from .mobile_api import (
    mobile_home, mobile_search, mobile_library, mobile_dj_stats,
    mobile_notifications, mobile_batch, mobile_track_detail,
    mobile_quick_buy, mobile_genres,
)
from .notification_views import (
    # Push Notifications
    register_push_subscription, unregister_push_subscription,
    notification_preferences, get_notifications, mark_notifications_read,
    # A/B Testing
    get_experiment_variant, track_experiment_event, get_user_experiments,
    admin_experiment_stats, admin_list_experiments, admin_create_experiment,
    admin_update_experiment_status,
)

urlpatterns = [
    # DJ Experience
    path('dj/quick-stats/', dj_quick_stats, name='dj_quick_stats'),
    path('dj/quick-upload/', quick_upload_track, name='quick_upload_track'),
    
    # Buyer Experience  
    path('search/', smart_search, name='smart_search'),
    path('feed/', homepage_feed, name='homepage_feed'),
    path('quick-checkout/', quick_checkout, name='quick_checkout'),
    
    # Admin Tools
    path('admin/stats/', admin_dashboard_stats, name='admin_stats'),
    path('admin/dj-approvals/', pending_dj_approvals, name='pending_approvals'),
    path('admin/dj-approve/<uuid:dj_id>/', quick_approve_dj, name='quick_approve_dj'),
    path('admin/flagged/', flagged_content, name='flagged_content'),
    
    # Mobile API (lightweight endpoints)
    path('m/home/', mobile_home, name='mobile_home'),
    path('m/search/', mobile_search, name='mobile_search'),
    path('m/library/', mobile_library, name='mobile_library'),
    path('m/dj/stats/', mobile_dj_stats, name='mobile_dj_stats'),
    path('m/notifications/', mobile_notifications, name='mobile_notifications'),
    path('m/batch/', mobile_batch, name='mobile_batch'),
    path('m/track/<uuid:track_id>/', mobile_track_detail, name='mobile_track_detail'),
    path('m/buy/', mobile_quick_buy, name='mobile_quick_buy'),
    path('m/genres/', mobile_genres, name='mobile_genres'),
    
    # Push Notifications
    path('notifications/', get_notifications, name='get_notifications'),
    path('notifications/read/', mark_notifications_read, name='mark_notifications_read'),
    path('notifications/preferences/', notification_preferences, name='notification_prefs'),
    path('push/subscribe/', register_push_subscription, name='push_subscribe'),
    path('push/unsubscribe/', unregister_push_subscription, name='push_unsubscribe'),
    
    # A/B Testing
    path('experiment/<str:experiment_name>/', get_experiment_variant, name='get_variant'),
    path('experiment/<str:experiment_name>/track/', track_experiment_event, name='track_event'),
    path('experiments/', get_user_experiments, name='user_experiments'),
    
    # A/B Testing Admin
    path('admin/experiments/', admin_list_experiments, name='admin_experiments'),
    path('admin/experiments/create/', admin_create_experiment, name='admin_create_experiment'),
    path('admin/experiments/<int:experiment_id>/status/', admin_update_experiment_status, name='admin_experiment_status'),
    path('admin/experiments/<str:experiment_name>/stats/', admin_experiment_stats, name='admin_experiment_stats'),
]
