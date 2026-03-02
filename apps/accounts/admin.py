from django.contrib import admin
from .models import User, Profile, DJProfile

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'role', 'is_staff', 'date_joined')
    search_fields = ('email',)
    list_filter = ('role', 'is_staff')

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
