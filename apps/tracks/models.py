from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.accounts.models import Profile, DJProfile


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
    checksum = models.CharField(max_length=64, null=True, blank=True)  # SHA-256 integrity [New]
    file_size = models.BigIntegerField(null=True, blank=True)  # Size in bytes
    
    FORMAT_CHOICES = (
        ('wav', 'WAV (Lossless)'),
        ('mp3', 'MP3 (320kbps)'),
        ('studio', 'Studio Project (ZIP)'),
        ('aiff', 'AIFF'),
    )
    file_format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default='wav')  # [Fix 17]

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
    sales_last_7_days = models.IntegerField(default=0)  # [Missing Item 01]
    
    # [Phase 3] External Link / Offload System
    is_external_link = models.BooleanField(default=False)
    external_link_url = models.URLField(max_length=1000, null=True, blank=True)
    external_link_provider = models.CharField(max_length=20, null=True, blank=True) # google_drive, mediafire, other
    external_link_broken = models.BooleanField(default=False)
    external_link_error = models.CharField(max_length=200, null=True, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['is_active', 'is_deleted']),
            models.Index(fields=['created_at']),
        ]

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        if self.price is None:
            raise ValidationError({"price": "Price is required."})

        # Allow free (₹0). If paid, enforce ₹19 minimum [Spec §3.2].
        if self.price > 0 and self.price < Decimal("19.00"):
            raise ValidationError({"price": "Paid track price must be at least ₹19."})

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

    def clean(self):
        super().clean()

        # Max 3 collaborators total [Spec P2 §4]
        existing = TrackCollaborator.objects.filter(track=self.track).exclude(pk=self.pk)
        if existing.count() >= 3:
            raise ValidationError("A track can have at most 3 collaborators.")

        # Revenue must sum to 100% across collaborators.
        total = Decimal("0.00")
        for c in existing:
            total += (c.revenue_percentage or Decimal("0.00"))
        total += (self.revenue_percentage or Decimal("0.00"))

        if total != Decimal("100.00"):
            raise ValidationError("Collaborator revenue percentages must sum to exactly 100.00.")


class TrackVersion(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='versions')
    version_label = models.CharField(max_length=100)
    file_key = models.CharField(max_length=500)
    checksum = models.CharField(max_length=255, null=True, blank=True)
    is_current = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class StarRating(models.Model):
    """Unified rating system (1-5 stars) [Fix 09]."""
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='ratings_given')
    content_type = models.CharField(max_length=20, choices=(('track', 'Track'), ('album', 'Album')))
    content_id = models.PositiveBigIntegerField()
    stars = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    review = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'content_type', 'content_id')
