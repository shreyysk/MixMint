from django.contrib import admin
from .models import AlbumPack, AlbumTrack, AlbumProcessingQueue

@admin.register(AlbumPack)
class AlbumPackAdmin(admin.ModelAdmin):
    list_display = ('title', 'dj', 'price', 'processing_status', 'track_count', 'created_at')
    list_filter = ('processing_status', 'upload_method')
    search_fields = ('title', 'dj__dj_name')

@admin.register(AlbumTrack)
class AlbumTrackAdmin(admin.ModelAdmin):
    list_display = ('title', 'album', 'track_order', 'format')

@admin.register(AlbumProcessingQueue)
class AlbumProcessingQueueAdmin(admin.ModelAdmin):
    list_display = ('album', 'status', 'attempts', 'created_at', 'completed_at')
