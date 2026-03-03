from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.accounts.models import DJProfile

class AlbumPack(models.Model):
    UPLOAD_METHODS = (
        ('system_generated', 'System Generated'),
        ('direct_zip', 'Direct ZIP'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('queued', 'Queued'),
    )
    
    dj = models.ForeignKey(DJProfile, on_delete=models.CASCADE, related_name='albums')
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('49.00'))],  # Minimum album price [Spec §4]
    )
    file_key = models.CharField(max_length=500)
    cover_image = models.URLField(max_length=500, null=True, blank=True)  # Cover image [Spec §6.2]

    # Preview URLs — DJ chooses type [Spec §2.1]
    PREVIEW_CHOICES = (
        ('youtube', 'YouTube'),
        ('instagram', 'Instagram Reel'),
    )
    preview_type = models.CharField(max_length=20, choices=PREVIEW_CHOICES, null=True, blank=True)
    youtube_url = models.URLField(max_length=500, null=True, blank=True)
    instagram_url = models.URLField(max_length=500, null=True, blank=True)

    is_active = models.BooleanField(default=True)  # Admin can disable content [Spec §3.3]
    is_deleted = models.BooleanField(default=False)  # Soft delete only [Spec P2 §3.2]
    upload_method = models.CharField(max_length=20, choices=UPLOAD_METHODS, default='direct_zip')
    original_file_key = models.CharField(max_length=500, null=True, blank=True)
    processing_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(null=True, blank=True)
    track_count = models.IntegerField(default=0)
    total_duration = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()

        # External preview is mandatory; no streaming allowed [Spec §2.1]
        if not self.preview_type:
            raise ValidationError({"preview_type": "Preview type is required (YouTube or Instagram)."})

        if self.preview_type == "youtube":
            if not self.youtube_url:
                raise ValidationError({"youtube_url": "YouTube preview URL is required."})
        elif self.preview_type == "instagram":
            if not self.instagram_url:
                raise ValidationError({"instagram_url": "Instagram Reel preview URL is required."})
        else:
            raise ValidationError({"preview_type": "Invalid preview type."})

class AlbumTrack(models.Model):
    album = models.ForeignKey(AlbumPack, on_delete=models.CASCADE, related_name='tracks')
    track_order = models.IntegerField()
    title = models.CharField(max_length=255)
    original_file_key = models.CharField(max_length=500, null=True, blank=True)
    processed_filename = models.CharField(max_length=255, null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    format = models.CharField(max_length=20, default='mp3')
    created_at = models.DateTimeField(auto_now_add=True)

class AlbumProcessingQueue(models.Model):
    album = models.ForeignKey(AlbumPack, on_delete=models.CASCADE, related_name='queue_items')
    status = models.CharField(max_length=20, default='queued')
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
