from django.core.cache import cache
from django.utils import timezone
from .models import FraudAlert
import logging

logger = logging.getLogger(__name__)

class FraudDetectionMiddleware:
    """ Detects suspicious activity patterns [Imp 03]. """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            self.track_user_activity(request)
        
        response = self.get_response(request)
        return response

    def track_user_activity(self, request):
        user = request.user.profile
        ip = self._get_client_ip(request)
        now = timezone.now()
        
        # 1. Track IPs per User (24h)
        user_ips_key = f"fraud_user_ips_{user.user.id}"
        ips = cache.get(user_ips_key, set())
        ips.add(ip)
        cache.set(user_ips_key, ips, timeout=86400)
        
        if len(ips) > 5:
            FraudAlert.objects.get_or_create(
                user=user,
                alert_type='ip_abuse',
                status='pending',
                defaults={
                    'severity': 'medium',
                    'details': {'ips': list(ips), 'reason': 'High number of IPs for single user'}
                }
            )

        # 2. Track Users per IP (24h)
        ip_users_key = f"fraud_ip_users_{ip.replace(':', '_')}"
        users = cache.get(ip_users_key, set())
        users.add(str(user.user.id))
        cache.set(ip_users_key, users, timeout=86400)
        
        if len(users) > 3:
            FraudAlert.objects.get_or_create(
                user=user,
                alert_type='ip_abuse',
                status='pending',
                defaults={
                    'severity': 'high',
                    'details': {'ip': ip, 'users': list(users), 'reason': 'Multiple users on same IP'}
                }
            )

    def _get_client_ip(self, request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
