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

import ipaddress
from django.core.cache import cache

def get_blacklist():
    cached = cache.get('ip_blacklist')
    if cached:
        return cached

    from apps.accounts.models import IPBlacklist

    ips = set(IPBlacklist.objects.filter(
        type='ip', is_active=True
    ).values_list('value', flat=True))

    cidrs = []
    for cidr_str in IPBlacklist.objects.filter(type='cidr', is_active=True).values_list('value', flat=True):
        try:
            cidrs.append(ipaddress.ip_network(cidr_str, strict=False))
        except ValueError:
            pass

    devices = set(IPBlacklist.objects.filter(
        type='device', is_active=True
    ).values_list('value', flat=True))

    blacklist = {'ips': ips, 'cidrs': cidrs, 'devices': devices}
    cache.set('ip_blacklist', blacklist, 300)  # 5 min cache
    return blacklist


class BlacklistMiddleware(MiddlewareMixin):
    """
    Missing Item 03 — Hard IP / Device Blacklist.
    Checks global IP/device/CIDR ban list on every request.
    Rejects banned IPs and device fingerprints.
    """

    def process_request(self, request):
        client_ip = self._get_client_ip(request)
        device_hash = request.META.get('HTTP_X_DEVICE_HASH') or request.headers.get('X-Device-Fingerprint', '')
        blacklist = get_blacklist()

        # Check exact IP
        if client_ip and client_ip in blacklist['ips']:
            return JsonResponse({'error': 'Access denied. Your IP has been blacklisted.', 'code': 'BLACKLISTED'}, status=403)

        # Check CIDR ranges
        if client_ip:
            try:
                ip_obj = ipaddress.ip_address(client_ip)
                for cidr in blacklist['cidrs']:
                    if ip_obj in cidr:
                        return JsonResponse({'error': 'Access denied. Your IP range has been blacklisted.', 'code': 'BLACKLISTED'}, status=403)
            except ValueError:
                pass

        # Check device
        if device_hash and device_hash in blacklist['devices']:
            return JsonResponse({'error': 'Access denied. Your device has been blacklisted.', 'code': 'BLACKLISTED'}, status=403)

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
        from django.shortcuts import render

        try:
            current_mode = MaintenanceMode.objects.order_by('-created_at').first()
            if not current_mode:
                return None

            is_api = 'api/v1' in request.path or request.content_type == 'application/json'

            if current_mode.mode == 'maintenance':
                if is_api:
                    return JsonResponse({
                        'error': 'Maintenance Mode Active.',
                        'message': current_mode.message or 'Scheduled maintenance.',
                        'code': 'MAINTENANCE_MODE'
                    }, status=503)
                
                return render(request, 'maintenance.html', {
                    'mode': 'maintenance',
                    'message': current_mode.message or 'Scheduled maintenance in progress.',
                    'estimated_return': current_mode.estimated_return_at,
                    'theme_color': 'amber' # Maintenance = Amber [Fix 14]
                }, status=503)

            elif current_mode.mode == 'kill_switch':
                # Kill switch — block downloads
                if '/downloads/' in request.path or '/download-token' in request.path:
                    if is_api:
                        return JsonResponse({
                            'error': 'Downloads Disabled.',
                            'code': 'KILL_SWITCH'
                        }, status=503)
                    
                    return render(request, 'maintenance.html', {
                        'mode': 'kill_switch',
                        'message': 'Downloads area is temporarily closed for security.',
                        'theme_color': 'red' # Kill Switch = Red [Fix 14]
                    }, status=503)
        except Exception:
            pass

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

class ReferralMiddleware(MiddlewareMixin):
    """
    Captures 'ref' parameter from URL and stores it in session [Imp 15].
    Used for DJ Ambassador Program.
    """

    def process_request(self, request):
        ref_code = request.GET.get('ref')
        if ref_code:
            request.session['ref_code'] = ref_code
        return None
