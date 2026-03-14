from django.urls import path
from .improvements import (
    # DJ Experience
    dj_quick_stats, quick_upload_track,
    # Buyer Experience
    smart_search, homepage_feed, quick_checkout,
    # Admin Tools
    admin_dashboard_stats, pending_dj_approvals, quick_approve_dj, flagged_content,
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
]
