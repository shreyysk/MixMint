from django.core.cache import cache
from .models import FraudAlert
import logging

logger = logging.getLogger(__name__)


class FraudDetectionMiddleware:
    """Detects suspicious activity patterns [Imp 03]."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                self.track_user_activity(request)
            except Exception:
                logger.exception("Fraud tracking failed")

        response = self.get_response(request)
        return response

    def track_user_activity(self, request):
        user = getattr(request.user, "profile", None)
        if user is None:
            return
        ip = self._get_client_ip(request) or "unknown"
        uid = str(user.user_id)

        # 1. Distinct IPs per user (24h)
        user_ips_key = f"fraud_user_ips_{uid}"
        ips = cache.get(user_ips_key, set())
        if ip not in ips:
            ips.add(ip)
            cache.set(user_ips_key, ips, timeout=86400)
            if len(ips) > 5 and cache.add(f"fraud_alerted_ips_{uid}", 1, timeout=86400):
                FraudAlert.objects.get_or_create(
                    user=user,
                    alert_type="ip_abuse",
                    status="pending",
                    defaults={
                        "severity": "medium",
                        "details": {"ips": sorted(ips)[:20], "reason": "High number of IPs for single user"},
                    },
                )

        # 2. Distinct users per IP (24h)
        ip_users_key = f"fraud_ip_users_{ip.replace(':', '_')}"
        users = cache.get(ip_users_key, set())
        if uid not in users:
            users.add(uid)
            cache.set(ip_users_key, users, timeout=86400)
            if len(users) > 3 and cache.add(f"fraud_alerted_ipusers_{ip}_{uid}", 1, timeout=86400):
                FraudAlert.objects.get_or_create(
                    user=user,
                    alert_type="ip_abuse",
                    status="pending",
                    defaults={
                        "severity": "medium",
                        "details": {"ip": ip, "user_count": len(users), "reason": "Multiple users on same IP"},
                    },
                )

    def _get_client_ip(self, request):
        from apps.core.net import get_client_ip

        return get_client_ip(request)


class FraudDetector:
    @staticmethod
    def check_purchase(user_id, data):
        """
        Runs fraud checks on a purchase transaction [BUG-07 FIX].
        Returns: (is_valid: bool, risk_level: str, flags: list)
        """
        ip = data.get("ip_address")
        device_hash = data.get("device_hash")
        content_id = data.get("content_id")

        flags = []
        risk_level = "low"

        # Rate check: Max 5 checkout transactions in a 5-minute window per user
        user_purchase_key = f"purchase_velocity_{user_id}"
        recent_purchases = cache.get(user_purchase_key, 0)
        if recent_purchases >= 5:
            flags.append("High checkout velocity")
            risk_level = "high"
        cache.set(user_purchase_key, recent_purchases + 1, timeout=300)

        # IP abuse checks
        if ip:
            ip_users_key = f"fraud_ip_users_{ip.replace(':', '_')}"
            users = cache.get(ip_users_key, set())
            if len(users) > 3:
                flags.append("Multiple distinct users from same IP")
                if risk_level != "high":
                    risk_level = "medium"

        # If high risk pattern detected, create a FraudAlert record
        if risk_level in ("medium", "high"):
            try:
                from apps.accounts.models import Profile

                profile = Profile.objects.get(user_id=user_id)
                FraudAlert.objects.get_or_create(
                    user=profile,
                    alert_type="ip_abuse" if "IP" in "".join(flags) else "velocity",
                    status="pending",
                    defaults={
                        "severity": risk_level,
                        "details": {"ip": ip, "flags": flags, "device_hash": device_hash, "content_id": content_id},
                    },
                )
            except Exception as e:
                logger.error(f"Error creating FraudAlert in FraudDetector: {str(e)}")

        # Block only if velocity is extremely abused
        if recent_purchases >= 10:
            return False, "high", flags + ["Extremely high checkout velocity (BLOCKED)"]

        return True, risk_level, flags
