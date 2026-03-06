from django.urls import path
from . import dashboard_views
from .frontend_views import HomeView, ExploreView, login_view, signup_view, logout_view
from .dashboard_views import dashboard_view, dj_dashboard_view
from .dj_views import dj_storefront_view
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', HomeView.as_view(), name='index'),
    path('home/', HomeView.as_view(), name='home'),
    path('explore/', ExploreView.as_view(), name='explore'),
    path('login/', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    path('logout/', logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', dashboard_view, name='dashboard'),
    path('dashboard/dj/', dj_dashboard_view, name='dj_dashboard'),
    path('apply-dj/', dashboard_views.dj_apply_view, name='apply_as_dj'),
    path('upload/', dashboard_views.upload_track_view, name='upload_track'),
    
    # DJ Storefront
    path('dj/<slug:slug>/', dj_storefront_view, name='dj_profile'),
    
    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
