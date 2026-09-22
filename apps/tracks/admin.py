from django.contrib import admin
from .models import Track, TrackPreview, TrackVersion


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    # SECURITY: source_url/source_type + legacy external_link_url are staff-only.
    # Never add them to list_display.
    list_display = ("title", "dj", "genre", "price", "download_count", "created_at")
    list_filter = ("genre", "is_active", "is_external_link")
    search_fields = ("title", "description", "dj__dj_name")
    readonly_fields = ("created_at",)
    fieldsets = (
        (None, {"fields": ("dj", "title", "description", "price", "file_key", "cover_url")}),
        ("Metadata", {"fields": ("duration_sec", "bpm", "genre", "year", "file_format", "file_size", "checksum")}),
        ("Preview", {"fields": ("preview_type", "youtube_url", "instagram_url")}),
        ("Status", {"fields": ("is_active", "is_deleted", "download_count", "sales_last_7_days")}),
        (
            "Backend source (STAFF ONLY — never exposed via API)",
            {
                "fields": ("is_external_link", "source_url", "source_type", "external_link_broken", "converted_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(TrackPreview)
class TrackPreviewAdmin(admin.ModelAdmin):
    list_display = ("track", "preview_type", "is_primary", "is_active")


@admin.register(TrackVersion)
class TrackVersionAdmin(admin.ModelAdmin):
    list_display = ("track", "version_label", "is_current", "created_at")
