"""
MixMint Content Archive Service [Spec §9].

Automatic archive of deleted content metadata.
When admin soft-deletes content, this service archives
the full content metadata before removal.
"""

from .models import ContentArchive


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
