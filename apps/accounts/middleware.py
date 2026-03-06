"""
MixMint Security Middleware [Spec §11, §13, P2 §15].

Three middleware classes:
1. IPSessionMiddleware — Logout on IP change
2. BanCheckMiddleware — Global IP/device ban enforcement
3. MaintenanceModeMiddleware — Platform mode checking
"""

from django.http import JsonResponse
from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin


class IPSessionMiddleware(MiddlewareMixin):
    """
    Stores client IP in session on login.
    Auto-logs out user if IP changes mid-session [Spec §13].
    """

    def process_request(self, request):
        if not request.user.is_authenticated:
            return None

        client_ip = self._get_client_ip(request)
        session_ip = request.session.get('bound_ip')

        if session_ip is None:
            # First request after login — bind IP
            request.session['bound_ip'] = client_ip
        elif session_ip != client_ip:
            # IP changed mid-session — force logout [Spec §13]
            logout(request)
            return JsonResponse({
                'error': 'Session terminated: IP address changed.',
                'code': 'IP_CHANGE_LOGOUT'
            }, status=401)

        return None

    @staticmethod
    def _get_client_ip(request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class BanCheckMiddleware(MiddlewareMixin):
    """
    Checks global IP/device ban list on every request [Spec §4.6].
    Rejects banned IPs and device fingerprints.
    """

    def process_request(self, request):
        from apps.admin_panel.models import BanList

        client_ip = self._get_client_ip(request)
        device_hash = request.META.get('HTTP_X_DEVICE_HASH')

        # Check IP ban
        if client_ip and BanList.objects.filter(
            ban_type='ip', value=client_ip, is_active=True
        ).exists():
            return JsonResponse({
                'error': 'Access denied. Your IP has been banned.',
                'code': 'IP_BANNED'
            }, status=403)

        # Check device ban
        if device_hash and BanList.objects.filter(
            ban_type='device', value=device_hash, is_active=True
        ).exists():
            return JsonResponse({
                'error': 'Access denied. Your device has been banned.',
                'code': 'DEVICE_BANNED'
            }, status=403)

        return None

    @staticmethod
    def _get_client_ip(request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class MaintenanceModeMiddleware(MiddlewareMixin):
    """
    Returns 503 if platform is in maintenance or kill-switch mode [Spec P2 §15].
    Admin routes are always accessible.
    """

    # Paths that bypass maintenance mode
    BYPASS_PATHS = ['/admin/', '/api/v1/admin/']

    def process_request(self, request):
        # Let admin paths through
        for path in self.BYPASS_PATHS:
            if request.path.startswith(path):
                return None

        from apps.admin_panel.models import MaintenanceMode

        try:
            current_mode = MaintenanceMode.objects.order_by('-created_at').first()
            if current_mode and current_mode.mode == 'maintenance':
                return JsonResponse({
                    'error': 'MixMint is currently under maintenance. Please try again later.',
                    'message': current_mode.message or 'Scheduled maintenance in progress.',
                    'code': 'MAINTENANCE_MODE'
                }, status=503)
            elif current_mode and current_mode.mode == 'kill_switch':
                # Kill switch — block download-related paths only
                if '/downloads/' in request.path or '/download-token' in request.path:
                    return JsonResponse({
                        'error': 'Downloads are temporarily disabled.',
                        'code': 'KILL_SWITCH'
                    }, status=503)
        except Exception:
            pass  # Don't crash on DB issues

        return None


class InactivityMiddleware(MiddlewareMixin):
    """
    Updates Profile.last_active_at on every request [Spec §10].
    Used to identify accounts for 12-month expiry.
    """

    def process_request(self, request):
        if request.user.is_authenticated:
            try:
                from django.utils import timezone
                # Update but don't force save on every single request if it's very recent
                # to save DB writes (e.g. only update if > 5 mins since last update)
                profile = request.user.profile
                now = timezone.now()
                if not profile.last_active_at or (now - profile.last_active_at).total_seconds() > 300:
                    profile.last_active_at = now
                    profile.save(update_fields=['last_active_at'])
            except Exception:
                pass
        return None
