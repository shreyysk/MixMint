from django.utils import timezone
from datetime import timedelta
from .models import FraudAlert, AuditLog
from apps.downloads.models import DownloadToken
from apps.commerce.models import Purchase

class SuspiciousActivityService:
    @staticmethod
    def log(activity_type, user_profile, ip_address=None, user_agent=None, resource_id=None, description=None):
        AuditLog.objects.create(
            action="SUSPICIOUS_ACTIVITY",
            target_id=user_profile.user.id,
            metadata={
                "type": activity_type,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "resource_id": str(resource_id) if resource_id else None,
                "description": description or "Suspicious activity detected"
            },
            ip_address=ip_address,
            user_agent=user_agent
        )

def detect_download_farming(profile, content_id):
    """Checks for excessive download attempts or token sharing."""
    # 1. Frequency check
    last_hour = timezone.now() - timedelta(hours=1)
    download_count = DownloadToken.objects.filter(
        user=profile,
        created_at__gte=last_hour
    ).count()

    if download_count > 10:
        FraudAlert.objects.create(
            user=profile,
            alert_type='download_farming',
            severity='high',
            details={'reason': 'Excessive downloads in last hour', 'count': download_count}
        )

    # 2. Token sharing check (same user, same content, >3 IPs in 24h)
    last_day = timezone.now() - timedelta(days=1)
    unique_ips = DownloadToken.objects.filter(
        user=profile,
        content_id=content_id,
        created_at__gte=last_day
    ).values_list('ip_address', flat=True).distinct().count()

    if unique_ips > 3:
        FraudAlert.objects.create(
            user=profile,
            alert_type='download_farming',
            severity='critical',
            details={'reason': 'Token sharing suspected (multiple IPs)', 'ip_count': unique_ips}
        )

def detect_payment_fraud(profile):
    """Checks for rapid retry attempts."""
    last_10m = timezone.now() - timedelta(minutes=10)
    failed_attempts = Purchase.objects.filter(
        user=profile,
        created_at__gte=last_10m,
        is_revoked=True # Assuming revoked/failed tracking
    ).count()

    if failed_attempts > 5:
        FraudAlert.objects.create(
            user=profile,
            alert_type='payment_fraud',
            severity='medium',
            details={'reason': 'Rapid payment retry attempts', 'count': failed_attempts}
        )
