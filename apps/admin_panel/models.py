from django.db import models
from apps.accounts.models import Profile, DJProfile


class SystemSetting(models.Model):
    key = models.CharField(max_length=255, primary_key=True)
    value = models.JSONField()
    description = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class AuditLog(models.Model):
    """Immutable admin action logs [Spec §7]"""
    admin = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name='admin_audit_logs')
    action = models.TextField()
    target_id = models.UUIDField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class FraudAlert(models.Model):
    SEVERITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )
    ALERT_TYPES = (
        ('download_farming', 'Download Farming'),
        ('payment_fraud', 'Payment Fraud'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('ip_abuse', 'IP Abuse'),
    )
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='fraud_alerts')
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    details = models.JSONField(default=dict)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)


class CopyrightReport(models.Model):
    """DMCA report tracking [Spec §10]"""
    reporter = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name='copyright_reports')
    track = models.ForeignKey('tracks.Track', on_delete=models.CASCADE, null=True, blank=True)
    album = models.ForeignKey('albums.AlbumPack', on_delete=models.CASCADE, null=True, blank=True)
    reason = models.TextField()
    evidence_url = models.URLField(null=True, blank=True)
    status = models.CharField(max_length=20, default='pending')
    admin_notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SupportTicket(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=255)
    category = models.CharField(max_length=50)
    priority = models.CharField(max_length=20, default='medium')
    status = models.CharField(max_length=20, default='open')
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class BanList(models.Model):
    """Hard ban list for IP + device [Spec §7]"""
    BAN_TYPES = (
        ('ip', 'IP Address'),
        ('device', 'Device Fingerprint'),
    )
    ban_type = models.CharField(max_length=20, choices=BAN_TYPES)
    value = models.CharField(max_length=255)  # IP address or device fingerprint
    reason = models.TextField(null=True, blank=True)
    banned_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name='bans_issued')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('ban_type', 'value')


class KillSwitch(models.Model):
    """Emergency download freeze [Spec §7, §11]"""
    is_active = models.BooleanField(default=False)
    activated_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name='kill_switches')
    reason = models.TextField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class MaintenanceMode(models.Model):
    """Platform mode switching [Spec P2 §15]"""
    MODE_CHOICES = (
        ('normal', 'Normal'),
        ('maintenance', 'Maintenance'),
        ('kill_switch', 'Kill Switch'),
    )
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='normal')
    message = models.TextField(null=True, blank=True)  # Custom message shown during maintenance
    activated_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name='maintenance_modes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


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

    def __str__(self):
        return f"Archive: {self.title} ({self.content_type})"

class PlatformSettings(models.Model):
    """Singleton model for global pricing and platform features [Spec P3 v3]"""
    # Pricing controls
    platform_commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=15.00)
    
    buyer_platform_fee_enabled = models.BooleanField(default=False)
    buyer_platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=5.00)
    
    gst_charging_enabled = models.BooleanField(default=False)
    
    dj_application_fee_enabled = models.BooleanField(default=False)
    dj_application_fee = models.DecimalField(max_digits=10, decimal_places=2, default=99.00)
    
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Platform Settings"


class PromotionalOffer(models.Model):
    """Dynamic occasion-based banner and offers [Spec P3 v3]"""
    is_active = models.BooleanField(default=False)
    title = models.CharField(max_length=255)  # e.g., "Launch Offer 🚀"
    tagline = models.CharField(max_length=255)  # e.g., "Zero platform fees. 10% comm"
    sub_text = models.CharField(max_length=255, null=True, blank=True)  # e.g., "Introductory launch pricing"
    badge_label = models.CharField(max_length=50, default="LIMITED TIME")
    occasion_tag = models.CharField(max_length=100, default="Launch")
    
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    
    # Placements
    show_on_homepage = models.BooleanField(default=True)
    show_on_navbar = models.BooleanField(default=True)
    show_on_dj_upload = models.BooleanField(default=True)
    show_on_checkout = models.BooleanField(default=True)
    show_on_track_pages = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

