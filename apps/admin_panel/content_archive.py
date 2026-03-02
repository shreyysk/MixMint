"""
MixMint Content Archive Service [Spec §9].

Automatic archive of deleted content metadata.
When admin soft-deletes content, this service archives
the full content metadata before removal.
"""

from django.db import models
from django.utils import timezone
from apps.accounts.models import DJProfile


class ContentArchive(models.Model):
    """Immutable archive of soft-deleted content [Spec §9]."""
    CONTENT_TYPES = (
        ('track', 'Track'),
        ('album', 'Album/ZIP'),
    )
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    content_id = models.PositiveBigIntegerField()
    dj = models.ForeignKey(DJProfile, on_delete=models.SET_NULL, null=True, related_name='archived_content')
    title = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict)  # Full content snapshot
    file_key = models.CharField(max_length=500)  # R2 path for potential recovery
    reason = models.TextField(null=True, blank=True)
    deleted_by = models.CharField(max_length=255, null=True, blank=True)
    archived_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'admin_panel'

    def __str__(self):
        return f"Archive: {self.title} ({self.content_type})"


def archive_content(content, content_type, reason='', deleted_by=''):
    """
    Archive content metadata before soft delete [Spec §9].
    Called from admin soft_delete_content view.
    """
    metadata = {
        'title': content.title,
        'price': str(content.price),
        'is_active': content.is_active,
        'created_at': content.created_at.isoformat(),
    }

    if content_type == 'track':
        metadata.update({
            'genre': getattr(content, 'genre', None),
            'year': getattr(content, 'year', None),
            'preview_type': getattr(content, 'preview_type', None),
            'youtube_url': getattr(content, 'youtube_url', None),
            'instagram_url': getattr(content, 'instagram_url', None),
            'download_count': content.download_count,
        })

    return ContentArchive.objects.create(
        content_type=content_type,
        content_id=content.id,
        dj=content.dj,
        title=content.title,
        metadata=metadata,
        file_key=content.file_key,
        reason=reason,
        deleted_by=deleted_by,
    )
