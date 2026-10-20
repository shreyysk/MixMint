"""
MixMint Security Middleware [Spec §11, §13, P2 §15].

Three middleware classes:
1. IPSessionMiddleware — Logout on IP change
2. BanCheckMiddleware — Global IP/device ban enforcement
3. MaintenanceModeMiddleware — Platform mode checking
"""

import ipaddress
import logging
from django.core.cache import cache
from django.http import JsonResponse
from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("mixmint")


def _network_of(ip):
    """Coarse network (/24 IPv4, /48 IPv6) so normal carrier/Wi-Fi churn doesn't log people out."""
    try:
        addr = ipaddress.ip_address(ip)
    except (TypeError, ValueError):
        return None
    prefix = 24 if addr.version == 4 else 48
    return str(ipaddress.ip_network(f"{addr}/{prefix}", strict=False))


class IPSessionMiddleware(MiddlewareMixin):
    """
    Binds a logged-in session to the client's network [Spec §13]. If the session
    suddenly appears from a different network it is terminated (stolen cookie
    defence). Same-network IP changes (DHCP/CGNAT) are allowed.
    """

    def process_request(self, request):
        if not request.user.is_authenticated:
            return None

        client_net = _network_of(self._get_client_ip(request))
        session_net = request.session.get("bound_net")

        if session_net is None:
            request.session["bound_net"] = client_net
        elif client_net and session_net != client_net:
            logger.warning("Session network changed for user %s; logging out.", request.user.pk)
            logout(request)
            if request.path.startswith("/api/") or request.headers.get("Accept", "").startswith("application/json"):
                return JsonResponse(
                    {
                        "error": "Session ended because your network changed. Please log in again.",
                        "code": "IP_CHANGE_LOGOUT",
                    },
                    status=401,
                )
            from django.shortcuts import redirect

            return redirect(f"/login/?next={request.path}&reason=network")
        return None

    @staticmethod
    def _get_client_ip(request):
        from apps.core.net import get_client_ip

        return get_client_ip(request)


def get_blacklist():
    cached = cache.get("ip_blacklist")
    if cached:
        return cached

    from apps.accounts.models import IPBlacklist

    ips = set(IPBlacklist.objects.filter(type="ip", is_active=True).values_list("value", flat=True))

    cidrs = []
    for cidr_str in IPBlacklist.objects.filter(type="cidr", is_active=True).values_list("value", flat=True):
        try:
            cidrs.append(ipaddress.ip_network(cidr_str, strict=False))
        except ValueError:
            pass

    devices = set(IPBlacklist.objects.filter(type="device", is_active=True).values_list("value", flat=True))

    blacklist = {"ips": ips, "cidrs": cidrs, "devices": devices}
    cache.set("ip_blacklist", blacklist, 300)  # 5 min cache
    return blacklist


class BlacklistMiddleware(MiddlewareMixin):
    """
    Missing Item 03 — Hard IP / Device Blacklist.
    Checks global IP/device/CIDR ban list on every request.
    Rejects banned IPs and device fingerprints.
    """

    def process_request(self, request):
        # Skip health check endpoint - it needs to be accessible without DB
        if request.path == "/health/":
            return None

        client_ip = self._get_client_ip(request)
        device_hash = request.META.get("HTTP_X_DEVICE_HASH") or request.headers.get("X-Device-Fingerprint", "")
        blacklist = get_blacklist()

        # Check exact IP
        if client_ip and client_ip in blacklist["ips"]:
            return JsonResponse(
                {"error": "Access denied. Your IP has been blacklisted.", "code": "BLACKLISTED"}, status=403
            )

        # Check CIDR ranges
        if client_ip:
            try:
                ip_obj = ipaddress.ip_address(client_ip)
                for cidr in blacklist["cidrs"]:
                    if ip_obj in cidr:
                        return JsonResponse(
                            {"error": "Access denied. Your IP range has been blacklisted.", "code": "BLACKLISTED"},
                            status=403,
                        )
            except ValueError:
                pass

        # Check device
        if device_hash and device_hash in blacklist["devices"]:
            return JsonResponse(
                {"error": "Access denied. Your device has been blacklisted.", "code": "BLACKLISTED"}, status=403
            )

        return None

    @staticmethod
    def _get_client_ip(request):
        from apps.core.net import get_client_ip

        return get_client_ip(request)


def current_platform_mode():
    """Latest MaintenanceMode row, cached briefly (checked on every request)."""
    cached = cache.get("platform_mode")
    if cached is not None:
        return cached or None
    from apps.admin_panel.models import MaintenanceMode

    row = MaintenanceMode.objects.order_by("-created_at").first()
    value = (
        {"mode": row.mode, "message": row.message, "estimated_return_at": row.estimated_return_at}
        if row and row.mode != "normal"
        else {}
    )
    cache.set("platform_mode", value, 15)
    return value or None


class MaintenanceModeMiddleware(MiddlewareMixin):
    """
    Returns 503 while the platform is in maintenance, or blocks downloads in
    kill-switch mode [Spec P2 §15]. Staff, the admin site (wherever ADMIN_URL
    points), login and static assets always pass.
    """

    def _bypass(self, request):
        from django.conf import settings

        admin_prefix = "/" + settings.ADMIN_URL.lstrip("/")
        paths = (
            admin_prefix,
            "/api/v1/admin/",
            "/static/",
            "/health/",
            "/login/",
            "/logout/",
            "/social-auth/",  # staff can still sign in with Google during maintenance
            "/csp-report/",
            "/telegram/webhook/",  # admins answer support from Telegram during maintenance too
            "/payment/webhook/",  # gateways confirming payments made just before maintenance
            "/payouts/webhook/",  # payout providers confirming transfers
        )
        if request.path.startswith(paths):
            return True
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.is_staff)

    def process_request(self, request):
        if self._bypass(request):
            return None
        try:
            current = current_platform_mode()
        except Exception:
            logger.exception("MaintenanceModeMiddleware: mode lookup failed; failing open.")
            return None
        if not current:
            return None

        from django.shortcuts import render

        is_api = request.path.startswith("/api/") or request.content_type == "application/json"
        if current["mode"] == "maintenance":
            if is_api:
                return JsonResponse(
                    {
                        "error": "Maintenance Mode Active.",
                        "message": current["message"] or "Scheduled maintenance.",
                        "code": "MAINTENANCE_MODE",
                    },
                    status=503,
                )
            return render(
                request,
                "maintenance.html",
                {
                    "mode": "maintenance",
                    "message": current["message"] or "Scheduled maintenance in progress.",
                    "estimated_return": current["estimated_return_at"],
                    "theme_color": "amber",
                },
                status=503,
            )
        if current["mode"] == "kill_switch" and ("/downloads/" in request.path or "/download-token" in request.path):
            if is_api:
                return JsonResponse({"error": "Downloads Disabled.", "code": "KILL_SWITCH"}, status=503)
            return render(
                request,
                "maintenance.html",
                {
                    "mode": "kill_switch",
                    "message": "Downloads area is temporarily closed for security.",
                    "theme_color": "red",
                },
                status=503,
            )
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
                    profile.save(update_fields=["last_active_at"])
            except Exception:
                pass
        return None


class ReferralMiddleware(MiddlewareMixin):
    """
    Captures 'ref' parameter from URL and stores it in session [Imp 15].
    Used for DJ Ambassador Program.
    """

    def process_request(self, request):
        ref_code = request.GET.get("ref", "")
        if ref_code and len(ref_code) <= 32 and ref_code.isalnum():
            request.session["ref_code"] = ref_code
        return None
