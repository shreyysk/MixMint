from django.contrib import admin
from .models import Track, TrackPreview, TrackVersion

@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('title', 'dj', 'genre', 'price', 'download_count', 'created_at')
    list_filter = ('genre', 'is_active')
    search_fields = ('title', 'description', 'dj__dj_name')

@admin.register(TrackPreview)
class TrackPreviewAdmin(admin.ModelAdmin):
    list_display = ('track', 'preview_type', 'is_primary', 'is_active')

@admin.register(TrackVersion)
class TrackVersionAdmin(admin.ModelAdmin):
    list_display = ('track', 'version_label', 'is_current', 'created_at')
