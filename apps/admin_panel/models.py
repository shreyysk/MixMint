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

