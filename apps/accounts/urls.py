from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, ProfileViewSet, DJProfileViewSet
from .frontend_views import HomeView, ExploreView, login_view, signup_view
from .dashboard_views import dashboard_view, dj_dashboard_view
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
    
    path('dj/<slug:slug>/', dj_storefront_view, name='dj_storefront'),
    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
