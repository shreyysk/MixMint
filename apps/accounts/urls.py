from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, ProfileViewSet, DJProfileViewSet
from .frontend_views import HomeView, ExploreView, login_view, signup_view
from .dashboard_views import (
    dashboard_view, dj_dashboard_view,
    add_custom_domain, check_custom_domain_status,
    enable_2fa, verify_2fa_setup,
    dj_onboarding, update_onboarding_step,
    export_user_data, request_account_deletion,
    active_sessions, logout_device
)
from .dj_views import dj_storefront_view
from django.contrib.auth import views as auth_views

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'profiles', ProfileViewSet)
router.register(r'djs', DJProfileViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Frontend Pages
    path('home/', HomeView.as_view(), name='home'),
    path('explore/', ExploreView.as_view(), name='explore'),
    path('login/', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    
    # Dashboard
    path('dashboard/', dashboard_view, name='dashboard'),
    path('dashboard/dj/', dj_dashboard_view, name='dj_dashboard'),
    path('dashboard/dj/domain/add/', add_custom_domain, name='add_custom_domain'),
    path('dashboard/dj/domain/status/', check_custom_domain_status, name='check_domain_status'),
    path('dashboard/dj/2fa/enable/', enable_2fa, name='enable_2fa'),
    path('dashboard/dj/2fa/verify/', verify_2fa_setup, name='verify_2fa'),
    path('dashboard/dj/onboarding/', dj_onboarding, name='dj_onboarding'),
    path('dashboard/dj/onboarding/update/', update_onboarding_step, name='update_onboarding'),
    path('privacy/export/', export_user_data, name='export_data'),
    path('privacy/delete/', request_account_deletion, name='request_deletion'),
    path('dashboard/sessions/', active_sessions, name='active_sessions'),
    path('dashboard/sessions/logout/', logout_device, name='logout_device'),
    
    path('dj/<slug:slug>/', dj_storefront_view, name='dj_storefront'),
    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
