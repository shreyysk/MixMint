from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, ProfileViewSet, DJProfileViewSet
from .dj_application_views import (
    apply_as_dj, admin_approve_dj, admin_reject_dj,
    admin_verify_dj, toggle_store_pause, request_payout_otp,
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'profiles', ProfileViewSet)
router.register(r'djs', DJProfileViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # DJ Application Flow [Spec §7]
    path('dj/apply/', apply_as_dj, name='dj_apply'),
    path('dj/<int:dj_profile_id>/approve/', admin_approve_dj, name='dj_approve'),
    path('dj/<int:dj_profile_id>/reject/', admin_reject_dj, name='dj_reject'),
    path('dj/<int:dj_profile_id>/verify/', admin_verify_dj, name='dj_verify'),
    path('dj/toggle-store/', toggle_store_pause, name='dj_toggle_store'),
    path('dj/payout-otp/', request_payout_otp, name='dj_payout_otp'),
    path('confirm-age/', UserViewSet.as_view({'post': 'confirm_age'}), name='user_confirm_age'),
]
