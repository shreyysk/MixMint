from django.db import models
from apps.accounts.models import Profile


from apps.commerce.models import Purchase


class DownloadToken(models.Model):
    """Secure one-time download token [Spec §4.5]"""
    token = models.CharField(max_length=255, primary_key=True)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='download_tokens')
    content_id = models.PositiveBigIntegerField()
    CONTENT_TYPES = (
        ('track', 'Track'),
        ('album', 'Album'),
    )
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_hash = models.CharField(max_length=255, null=True, blank=True)  # Device fingerprint [Spec §4.5]
    user_agent = models.TextField(null=True, blank=True)
    is_used = models.BooleanField(default=False)
    access_source = models.CharField(max_length=50)  # 'purchase' or 'redownload'
    download_completed = models.BooleanField(default=False)  # Byte verification [Spec §4.4]
    bytes_expected = models.BigIntegerField(null=True, blank=True)
    bytes_delivered = models.BigIntegerField(null=True, blank=True)
    checksum_verified = models.BooleanField(default=False)  # Checksum match [Spec §4.4]
    checksum_hex = models.CharField(max_length=64, null=True, blank=True)  # SHA-256 of delivered file
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['expires_at'], condition=models.Q(is_used=False), name='idx_download_tokens_expiry'),
        ]


class DownloadAttempt(models.Model):
    """Per-IP attempt tracking [Spec §4.2: 3 attempts per IP per content]"""
    ip_address = models.GenericIPAddressField()
    content_id = models.PositiveBigIntegerField()
    CONTENT_TYPES = (
        ('track', 'Track'),
        ('album', 'Album'),
    )
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    attempt_count = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('ip_address', 'content_id', 'content_type')


class DownloadLog(models.Model):
    """Detailed download audit log [Spec P2 §6]"""
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='download_logs')
    content_id = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=20)
    ip_address = models.GenericIPAddressField()
    device_hash = models.CharField(max_length=255, null=True, blank=True)
    attempt_number = models.IntegerField(default=1)
    completed = models.BooleanField(default=False)
    checksum_verified = models.BooleanField(default=False)
    checksum_hex = models.CharField(max_length=64, null=True, blank=True)
    bytes_delivered = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class DownloadInsurance(models.Model):
    """Optional download insurance — unlimited re-downloads [Spec §4.3]."""
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('claimed', 'Claimed'),
    )
    purchase = models.OneToOneField(Purchase, on_delete=models.CASCADE, related_name='insurance')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='download_insurances')
    content_id = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=20)
    insurance_price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_id = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    claims_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Insurance for Purchase #{self.purchase_id}"
