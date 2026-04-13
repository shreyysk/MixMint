"""
MixMint Security Middleware [Phase 3 Security Fixes].

Handles:
- EX-01.02: Token reuse prevention (already in DownloadManager)
- EX-01.03: IP bypass detection via header spoofing
- EX-02.01: Fraud detection for rapid downloads
- EX-02.02: Account velocity checks
- Maintenance mode enforcement
"""

import re
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings


class SecurityMiddleware:
    """
    Security middleware for fraud detection and abuse prevention.
    """
    
    # Suspicious header patterns for IP spoofing detection [EX-01.03]
    SUSPICIOUS_HEADERS = [
        'HTTP_X_ORIGINATING_IP',
        'HTTP_X_REMOTE_IP', 
        'HTTP_X_CLIENT_IP',
        'HTTP_X_HOST',
        'HTTP_X_FORWARDED_HOST',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # 1. Check maintenance mode
        if self._is_maintenance_mode() and not self._is_admin(request):
            if request.path.startswith('/api/'):
                return JsonResponse({
                    'error': 'Platform is under maintenance. Please try again later.',
                    'code': 'MAINTENANCE_MODE'
                }, status=503)
        
        # 2. IP spoofing detection [EX-01.03 FIX]
        if self._detect_ip_spoofing(request):
            self._log_security_event(request, 'ip_spoofing_attempt')
            return JsonResponse({
                'error': 'Security violation detected.',
                'code': 'SECURITY_VIOLATION'
            }, status=403)
        
        # 3. Rapid download detection [EX-02.01 FIX]
        if request.path.startswith('/download/'):
            client_ip = self._get_client_ip(request)
            if self._is_rapid_downloader(client_ip):
                return JsonResponse({
                    'error': 'Too many download requests. Please slow down.',
                    'code': 'RATE_LIMITED'
                }, status=429)
        
        return self.get_response(request)
    
    def _is_maintenance_mode(self):
        """Check if platform is in maintenance mode."""
        from apps.admin_panel.models import MaintenanceMode
        latest = MaintenanceMode.objects.last()
        return latest and latest.mode != 'normal'
    
    def _is_admin(self, request):
        """Check if request is from admin."""
        return hasattr(request, 'user') and request.user.is_authenticated and request.user.is_staff
    
    def _detect_ip_spoofing(self, request):
        """
        [EX-01.03 FIX] Detect IP spoofing via header manipulation.
        Returns True if spoofing detected.
        """
        # Check for suspicious headers that shouldn't be client-controllable
        for header in self.SUSPICIOUS_HEADERS:
            if request.META.get(header):
                return True
        
        # Check X-Forwarded-For for multiple IPs (potential spoofing)
        xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if xff and xff.count(',') > 3:  # More than 3 proxies is suspicious
            return True
            
        return False
    
    def _is_rapid_downloader(self, client_ip):
        """
        [EX-02.01 FIX] Detect rapid download patterns (bot behavior).
        Max 10 download requests per minute per IP.
        """
        cache_key = f"dl_rate_{client_ip}"
        current = cache.get(cache_key, 0)
        
        if current >= 10:
            return True
            
        cache.set(cache_key, current + 1, timeout=60)
        return False
    
    def _get_client_ip(self, request):
        """Get real client IP."""
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def _log_security_event(self, request, event_type):
        """Log security event for audit."""
        from apps.admin_panel.models import AuditLog
        try:
            AuditLog.objects.create(
                admin=None,
                action=f"Security: {event_type}",
                ip_address=self._get_client_ip(request),
                metadata={
                    'path': request.path,
                    'method': request.method,
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
                }
            )
        except Exception:
            pass


class AccountVelocityMiddleware:
    """
    [EX-02.02 FIX] Detect suspicious account activity patterns.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Only check authenticated users on sensitive endpoints
        if request.user.is_authenticated and request.path.startswith('/api/'):
            if self._check_velocity(request.user):
                return JsonResponse({
                    'error': 'Unusual activity detected. Please try again later.',
                    'code': 'VELOCITY_CHECK'
                }, status=429)
        
        return self.get_response(request)
    
    def _check_velocity(self, user):
        """
        Check for suspicious activity velocity.
        Max 100 API requests per minute per user.
        """
        cache_key = f"api_velocity_{user.id}"
        current = cache.get(cache_key, 0)
        
        if current >= 100:
            return True
            
        cache.set(cache_key, current + 1, timeout=60)
        return False
