"""
MixMint Real-Time Fraud Alert System [Phase 3 Enhancement].

Sends instant email notifications to admins for high-severity security events.
"""

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class FraudAlertNotifier:
    """Real-time fraud alert notification system."""
    
    SEVERITY_THRESHOLDS = {
        'critical': True,   # Always notify
        'high': True,       # Always notify
        'medium': False,    # Batch daily
        'low': False,       # Log only
    }
    
    @staticmethod
    def notify_admins(alert):
        """
        Send real-time notification to admins for high-severity alerts.
        """
        if not FraudAlertNotifier.SEVERITY_THRESHOLDS.get(alert.severity, False):
            return False
            
        try:
            # Get admin emails
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admin_emails = list(
                User.objects.filter(is_staff=True, is_active=True)
                .values_list('email', flat=True)
            )
            
            if not admin_emails:
                logger.warning("No admin emails found for fraud alert notification")
                return False
            
            # Build email content
            subject = f"🚨 [{alert.severity.upper()}] MixMint Security Alert - {alert.alert_type}"
            
            context = {
                'alert': alert,
                'user_email': alert.user.user.email if alert.user else 'Unknown',
                'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
                'details': alert.details or {},
                'dashboard_url': f"{settings.BASE_URL}/admin/fraud-alerts/{alert.id}/",
            }
            
            # Plain text email
            message = f"""
SECURITY ALERT - {alert.severity.upper()}

Type: {alert.alert_type}
User: {context['user_email']}
Time: {context['timestamp']}

Details:
{alert.details}

Action Required: Review this alert in the admin dashboard.
Dashboard: {context['dashboard_url']}

---
MixMint Security System
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
                fail_silently=False,
            )
            
            # Mark alert as notified
            alert.admin_notified = True
            alert.notified_at = timezone.now()
            alert.save(update_fields=['admin_notified', 'notified_at'])
            
            logger.info(f"Fraud alert {alert.id} notification sent to {len(admin_emails)} admins")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send fraud alert notification: {str(e)}")
            return False
    
    @staticmethod
    def send_daily_digest():
        """Send daily digest of medium/low severity alerts."""
        from apps.admin_panel.models import FraudAlert
        
        yesterday = timezone.now() - timezone.timedelta(days=1)
        alerts = FraudAlert.objects.filter(
            created_at__gte=yesterday,
            severity__in=['medium', 'low'],
            admin_notified=False
        )
        
        if not alerts.exists():
            return
            
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin_emails = list(
            User.objects.filter(is_staff=True, is_active=True)
            .values_list('email', flat=True)
        )
        
        if not admin_emails:
            return
            
        subject = f"📊 MixMint Daily Security Digest - {alerts.count()} alerts"
        message = f"""
DAILY SECURITY DIGEST

Total Alerts (24h): {alerts.count()}

Summary:
- Medium severity: {alerts.filter(severity='medium').count()}
- Low severity: {alerts.filter(severity='low').count()}

Please review these in the admin dashboard.

---
MixMint Security System
        """
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
                fail_silently=False,
            )
            alerts.update(admin_notified=True, notified_at=timezone.now())
        except Exception as e:
            logger.error(f"Failed to send daily digest: {str(e)}")
