from django.contrib import admin
from .models import User, Profile, DJProfile, DJApplication

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'get_role', 'is_staff', 'date_joined')
    search_fields = ('email',)
    list_filter = ('profile__role', 'is_staff')

    @admin.display(description="role")
    def get_role(self, obj):
        try:
            return obj.profile.role
        except Exception:
            return None

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'is_frozen', 'created_at')
    search_fields = ('full_name', 'user__email')

@admin.register(DJProfile)
class DJProfileAdmin(admin.ModelAdmin):
    list_display = ('dj_name', 'slug', 'status', 'total_revenue', 'created_at')
    list_filter = ('status',)
    search_fields = ('dj_name', 'slug')
    prepopulated_fields = {'slug': ('dj_name',)}


@admin.register(DJApplication)
class DJApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'paid_application_fee', 'created_at', 'reviewed_at')
    list_filter = ('status', 'paid_application_fee')
    search_fields = ('user__user__email', 'user__full_name')


from .models import IPBlacklist

@admin.register(IPBlacklist)
class IPBlacklistAdmin(admin.ModelAdmin):
    list_display = ('type', 'value', 'is_active', 'added_by', 'created_at')
    list_filter = ('type', 'is_active')
    search_fields = ('value', 'reason')

from .models import DJPageView

@admin.register(DJPageView)
class DJPageViewAdmin(admin.ModelAdmin):
    list_display = ('dj', 'page_type', 'ip_address', 'created_at')
    list_filter = ('page_type', 'created_at')
    search_fields = ('dj__dj_name', 'ip_address')
