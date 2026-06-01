from rest_framework.permissions import BasePermission

class IsDJ(BasePermission):
    """Allow access only to approved DJs."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            hasattr(request.user, 'profile') and
            request.user.profile.role == 'dj' and
            not request.user.profile.is_banned and
            not request.user.profile.is_frozen and
            hasattr(request.user.profile, 'dj_profile') and
            request.user.profile.dj_profile.status == 'approved'
        )

class IsProDJ(IsDJ):
    """Allow access only to Pro DJs."""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.profile.is_pro_dj

class IsAdmin(BasePermission):
    """Allow access only to platform admins."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (request.user.is_staff or
             (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'))
        )

class IsOwnerDJ(BasePermission):
    """Object-level: DJ can only modify their own content."""
    def has_object_permission(self, request, view, obj):
        if not hasattr(request.user, 'profile'):
            return False
        try:
            return obj.dj == request.user.profile.dj_profile
        except AttributeError:
            return False

class IsBuyer(BasePermission):
    """User has purchased this content."""
    def has_object_permission(self, request, view, obj):
        from apps.commerce.models import Purchase
        return Purchase.objects.filter(
            user=request.user.profile,
            content_id=obj.id,
            status='paid',
        ).exists()

class IsNotBanned(BasePermission):
    """Reject banned or frozen accounts."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return True  # Let auth handle unauthenticated
        profile = getattr(request.user, 'profile', None)
        if profile and (profile.is_banned or profile.is_frozen):
            return False
        return True
