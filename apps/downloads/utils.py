import logging
import secrets
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import DownloadAttempt, DownloadLog, DownloadToken

logger = logging.getLogger("mixmint")


class DownloadManager:
    """
    Secure download manager for MixMint v2.0.
    Ownership-based access only (paid, non-revoked purchases). No subscriptions. No quotas.
    """

    # ------------------------------------------------------------------ tokens
    @staticmethod
    def generate_token(profile, content_id, content_type, access_source, ip_address, user_agent, device_hash=None):
        """One-time download token, short expiry [Spec §4.5]."""
        minutes = getattr(settings, "DOWNLOAD_TOKEN_EXPIRY_MINUTES", 5)
        return DownloadToken.objects.create(
            token=secrets.token_hex(32),
            user=profile,
            content_id=content_id,
            content_type=content_type,
            access_source=access_source,
            ip_address=ip_address,
            device_hash=(device_hash or None) and str(device_hash)[:255],
            user_agent=(user_agent or "")[:1000],
            expires_at=timezone.now() + timedelta(minutes=minutes),
        )

    @staticmethod
    def owned_purchase(profile, content_id, content_type):
        """Latest *paid*, non-revoked original purchase — the only thing that grants access."""
        from apps.commerce.models import Purchase

        return (
            Purchase.objects.filter(
                user=profile,
                content_id=content_id,
                content_type=content_type,
                status="paid",
                is_revoked=False,
                is_redownload=False,
            )
            .order_by("-created_at")
            .first()
        )

    @staticmethod
    def has_active_insurance(purchase):
        ins = getattr(purchase, "insurance", None) if purchase else None
        return bool(ins and ins.status == "active")

    @classmethod
    def issue_token_response(cls, request, content, content_type):
        """
        Shared download-token endpoint for tracks and albums [Spec §4].
        Returns a DRF Response.
        """
        from rest_framework.response import Response

        from apps.core.net import get_client_ip

        profile = request.user.profile
        client_ip = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        device_hash = request.data.get("device_hash") or request.META.get("HTTP_X_DEVICE_HASH")

        if profile.is_frozen or profile.is_banned:
            return Response({"error": "Your account is restricted. Contact support."}, status=403)

        is_banned, ban_msg = cls.check_ban_list(client_ip, device_hash)
        if is_banned:
            return Response({"error": ban_msg}, status=403)

        purchase = cls.owned_purchase(profile, content.id, content_type)
        is_free = Decimal(content.price) <= 0
        if not purchase and not is_free:
            return Response(
                {"error": f"You must purchase this {content_type} first.", "price": str(content.price)}, status=403
            )

        access_source = "free" if (is_free and not purchase) else "purchase"
        redownload_price = str((Decimal(content.price) * Decimal("0.5")).quantize(Decimal("0.01")))

        if purchase and purchase.download_completed:
            if cls.has_active_insurance(purchase):
                access_source = "insurance"
            else:
                eligible, msg = cls.check_redownload_eligibility(profile, content.id, content_type)
                if eligible:
                    return Response(
                        {
                            "error": "Re-download requires payment.",
                            "redownload_available": True,
                            "redownload_price": redownload_price,
                            "message": msg,
                        },
                        status=402,
                    )
                return Response({"error": msg}, status=403)

        if access_source != "insurance":
            allowed, msg, remaining = cls.check_ip_attempts(client_ip, content.id, content_type, user=profile)
            if not allowed:
                eligible, _ = cls.check_redownload_eligibility(profile, content.id, content_type)
                payload = {"error": msg}
                if eligible and not is_free:
                    payload.update(
                        {
                            "redownload_available": True,
                            "redownload_price": redownload_price,
                            "message": "You can re-download at 50% price.",
                        }
                    )
                return Response(payload, status=403)
        else:
            msg, remaining = None, None

        # Files older than the R2 hold live only in Telegram: fetch it back before issuing a link.
        from apps.admin_panel.vault import ensure_in_r2

        if not ensure_in_r2(content_type, content):
            return Response(
                {"preparing": True, "retry_after": 5,
                 "message": "Fetching your file from the MixMint vault. This usually takes under a minute."},
                status=202,
            )
        token = cls.generate_token(profile, content.id, content_type, access_source, client_ip, user_agent, device_hash)
        data = {
            "download_url": f"/api/v1/downloads/{token.token}/",
            "page_url": f"/api/v1/downloads/page/{token.token}/",
            "expires_in_seconds": getattr(settings, "DOWNLOAD_TOKEN_EXPIRY_MINUTES", 5) * 60,
        }
        if msg:
            data["warning"] = msg
        if remaining == 1:
            data["warning"] = "This is your last download attempt from this network."
        return Response(data)

    @staticmethod
    def validate_and_use(token_str, client_ip, device_hash=None):
        """
        Atomically claim a token (single use, even under concurrent requests).
        IP must match; a *different network AND different device* is treated as a
        shared link and flags + freezes the account [Spec §4.5]. A network change
        alone (mobile data, Wi-Fi hand-off) only rejects the token.
        """
        now = timezone.now()
        with transaction.atomic():
            token = (
                DownloadToken.objects.select_for_update()
                .filter(token=token_str, is_used=False, expires_at__gt=now)
                .select_related("user")
                .first()
            )
            if token is None:
                raise ValueError("Invalid, expired, or already used link. Generate a new one from your library.")

            ip_mismatch = bool(token.ip_address and client_ip and token.ip_address != client_ip)
            device_mismatch = bool(token.device_hash and device_hash and token.device_hash != device_hash)

            shared = ip_mismatch and device_mismatch
            if shared or not (ip_mismatch or device_mismatch):
                # Burn the token either way: a shared link must never work afterwards.
                token.is_used = True
                token.save(update_fields=["is_used"])

        # Outside the atomic block so the freeze is not rolled back by the raise.
        if shared:
            DownloadManager._trigger_misuse_freeze(
                token.user,
                "shared_link",
                f"Token IP {token.ip_address} / device {token.device_hash[:8]}… used from {client_ip} "
                f"/ {device_hash[:8]}…",
            )
            raise ValueError("This download link was issued to another device. Account flagged for review.")
        if ip_mismatch or device_mismatch:
            raise ValueError("Your network or device changed since the link was created. Please generate a new one.")
        return token

    @staticmethod
    def _trigger_misuse_freeze(profile, misuse_type, details):
        from apps.admin_panel.models import FraudAlert

        FraudAlert.objects.create(
            user=profile,
            alert_type="suspicious_activity",
            severity="high",
            details={"misuse_type": misuse_type, "details": details},
            status="pending",
        )
        profile.is_frozen = True
        profile.save(update_fields=["is_frozen"])

    # ---------------------------------------------------------------- attempts
    @staticmethod
    def check_ip_attempts(ip_address, content_id, content_type, max_attempts=None, user=None):
        """3 attempts per user + network + item [Spec §4.2]. Per-user so shared NATs don't block strangers."""
        max_attempts = max_attempts or getattr(settings, "MAX_DOWNLOAD_ATTEMPTS", 3)
        attempt = DownloadAttempt.objects.filter(
            user=user, ip_address=ip_address, content_id=content_id, content_type=content_type
        ).first()
        used = attempt.attempt_count if attempt else 0
        remaining = max_attempts - used
        if remaining <= 0:
            return False, f"Download attempt limit reached ({max_attempts}/{max_attempts}) on this network.", 0
        warning = None
        if remaining == 1:
            warning = "WARNING: This is your last download attempt for this content from this network."
        return True, warning, remaining

    @staticmethod
    def increment_attempt(ip_address, content_id, content_type, user=None):
        from django.db.models import F

        attempt, _ = DownloadAttempt.objects.get_or_create(
            user=user, ip_address=ip_address, content_id=content_id, content_type=content_type
        )
        DownloadAttempt.objects.filter(pk=attempt.pk).update(attempt_count=F("attempt_count") + 1)
        attempt.refresh_from_db(fields=["attempt_count"])
        return attempt.attempt_count

    @staticmethod
    def reset_attempts(user, content_id, content_type):
        DownloadAttempt.objects.filter(user=user, content_id=content_id, content_type=content_type).delete()

    @staticmethod
    def create_download_log(user, content_id, content_type, ip_address, device_hash=None, attempt_number=1):
        return DownloadLog.objects.create(
            user=user,
            content_id=content_id,
            content_type=content_type,
            ip_address=ip_address,
            device_hash=device_hash,
            attempt_number=attempt_number,
        )

    # -------------------------------------------------------------- re-download
    @staticmethod
    def check_redownload_eligibility(profile, content_id, content_type):
        """
        [Spec §4.3] After a completed download: 3-day lock, then re-download at 50%.
        Insurance = free unlimited re-downloads.
        """
        purchase = DownloadManager.owned_purchase(profile, content_id, content_type)
        if not purchase:
            return False, "No completed purchase found."
        if DownloadManager.has_active_insurance(purchase):
            return True, "Download Insurance active. Unlimited free re-downloads available."
        if not purchase.download_completed:
            return True, "Previous download failed or not completed. Free retry available."
        lock_expiry = (purchase.paid_at or purchase.created_at) + timedelta(days=getattr(settings, "IP_LOCK_DAYS", 3))
        if timezone.now() < lock_expiry:
            return (
                False,
                "Re-download lock active. Try again 3 days after purchase (or buy Download Insurance).",
            )
        return True, "Re-download available at 50% price."

    @staticmethod
    def mark_download_complete(token, bytes_delivered, checksum_hex=None, checksum_ok=True):
        """Byte + checksum verified completion [Spec §4.4]."""
        from apps.commerce.models import Purchase

        token.download_completed = bool(checksum_ok)
        token.bytes_delivered = bytes_delivered
        token.checksum_verified = bool(checksum_ok)
        token.checksum_hex = checksum_hex
        token.save()

        if checksum_ok:
            latest = (
                Purchase.objects.filter(
                    user=token.user,
                    content_id=token.content_id,
                    content_type=token.content_type,
                    status="paid",
                    download_completed=False,
                )
                .order_by("-created_at")
                .values_list("pk", flat=True)[:5]
            )
            Purchase.objects.filter(pk__in=list(latest)).update(download_completed=True)

        log = (
            DownloadLog.objects.filter(
                user=token.user, content_id=token.content_id, content_type=token.content_type, completed=False
            )
            .order_by("-created_at")
            .first()
        )
        if log:
            log.completed = bool(checksum_ok)
            log.checksum_verified = bool(checksum_ok)
            log.checksum_hex = checksum_hex
            log.bytes_delivered = bytes_delivered
            log.save()

    @staticmethod
    def check_ban_list(ip_address, device_hash=None):
        from apps.admin_panel.models import BanList

        if ip_address and BanList.objects.filter(ban_type="ip", value=ip_address, is_active=True).exists():
            return True, "Your IP address has been banned."
        if device_hash and BanList.objects.filter(ban_type="device", value=device_hash, is_active=True).exists():
            return True, "Your device has been banned."
        return False, None
