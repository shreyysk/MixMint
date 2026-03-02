from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.accounts.models import DJProfile


class Track(models.Model):
    dj = models.ForeignKey(DJProfile, on_delete=models.CASCADE, related_name='tracks')
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],  # 0 = free, min paid = ₹19 enforced in views
    )
    file_key = models.CharField(max_length=500)  # Private R2 path
    cover_url = models.URLField(max_length=500, null=True, blank=True)
    duration_sec = models.IntegerField(null=True, blank=True)
    bpm = models.IntegerField(null=True, blank=True)
    genre = models.CharField(max_length=100, null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)  # Release year [Spec P2 §3.1]

    # Preview URLs — DJ chooses type [Spec §2.1]
    PREVIEW_CHOICES = (
        ('youtube', 'YouTube'),
        ('instagram', 'Instagram Reel'),
    )
    preview_type = models.CharField(max_length=20, choices=PREVIEW_CHOICES, null=True, blank=True)
    youtube_url = models.URLField(max_length=500, null=True, blank=True)
    instagram_url = models.URLField(max_length=500, null=True, blank=True)

    is_active = models.BooleanField(default=True)  # Admin/DJ can disable [Spec §3.2, §3.3]
    is_deleted = models.BooleanField(default=False)  # Soft delete only [Spec P2 §3.1]
    download_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class TrackPreview(models.Model):
    """External preview embeds only — no hosted previews [Spec §2.1]"""
    PREVIEW_TYPES = (
        ('youtube', 'YouTube'),
        ('instagram_reel', 'Instagram Reel'),
    )
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='previews')
    preview_type = models.CharField(max_length=20, choices=PREVIEW_TYPES)
    url = models.URLField(max_length=500)
    embed_id = models.CharField(max_length=255)
    embed_html = models.TextField(null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TrackCollaborator(models.Model):
    """Collaboration engine — max 3 DJs per track [Spec P2 §4]"""
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='collaborators')
    dj = models.ForeignKey(DJProfile, on_delete=models.CASCADE, related_name='collaborations')
    revenue_percentage = models.DecimalField(max_digits=5, decimal_places=2)  # Must sum to 100%

    class Meta:
        unique_together = ('track', 'dj')


class TrackVersion(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='versions')
    version_label = models.CharField(max_length=100)
    file_key = models.CharField(max_length=500)
    checksum = models.CharField(max_length=255, null=True, blank=True)
    is_current = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
