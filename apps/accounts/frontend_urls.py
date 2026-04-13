from django.urls import path
from django.shortcuts import render
from . import dashboard_views
from .frontend_views import HomeView, ExploreView, DJDirectoryView, login_view, signup_view, logout_view, WaitlistSignupView
from .dashboard_views import (
    dashboard_view, dj_dashboard_view,
    bundle_management_view, create_bundle_view,
    announcement_management_view, create_announcement_view, delete_announcement_view,
    ambassador_management_view, generate_ambassador_code_view
)
from .dj_views import dj_storefront_view
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', HomeView.as_view(), name='index'),
    path('home/', HomeView.as_view(), name='home'),
    path('explore/', ExploreView.as_view(), name='explore'),
    path('djs/', DJDirectoryView.as_view(), name='dj_directory'),
    path('login/', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    path('logout/', logout_view, name='logout'),
    path('waitlist/signup/', WaitlistSignupView.as_view(), name='waitlist_signup'),
    path('contact/', lambda r: render(r, 'contact.html'), name='contact'),
    
    # Dashboard
    path('dashboard/', dashboard_view, name='dashboard'),
    path('dashboard/dj/', dj_dashboard_view, name='dj_dashboard'),
    path('apply-dj/', dashboard_views.dj_apply_view, name='apply_as_dj'),
    path('upload/', dashboard_views.upload_track_view, name='upload_track'),
    path('dashboard/bundles/', bundle_management_view, name='bundle_management'),
    path('dashboard/bundles/create/', create_bundle_view, name='create_bundle'),
    path('dashboard/announcements/', announcement_management_view, name='announcement_management'),
    path('dashboard/announcements/create/', create_announcement_view, name='create_announcement'),
    path('dashboard/announcements/delete/<int:post_id>/', delete_announcement_view, name='delete_announcement'),
    path('dashboard/ambassador/', ambassador_management_view, name='ambassador_management'),
    path('dashboard/ambassador/generate/', generate_ambassador_code_view, name='generate_ambassador_code'),

    # Library [Spec §9]
    path('library/', lambda r: render(r, 'commerce/library.html'), name='library_page'),
    
    # DJ Storefront
    path('dj/<slug:slug>/', dj_storefront_view, name='dj_profile'),
    
    # Password Reset (MixMint-styled templates)
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html',
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html',
    ), name='password_reset_complete'),
]
