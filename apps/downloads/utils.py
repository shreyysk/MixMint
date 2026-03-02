import secrets
from datetime import timedelta

from django.utils import timezone

from .models import DownloadToken, DownloadAttempt, DownloadLog


class DownloadManager:
    """
    Secure download manager for MixMint v2.0.
    Ownership-based access only. No subscriptions. No quotas.
    """

    @staticmethod
    def generate_token(profile, content_id, content_type, access_source, ip_address, user_agent, device_hash=None):
        """Generate a one-time download token with 5-minute expiry [Spec §4.5]."""
        token = secrets.token_hex(32)
        expires_at = timezone.now() + timedelta(minutes=5)

        return DownloadToken.objects.create(
            token=token,
            user=profile,
            content_id=content_id,
            content_type=content_type,
            access_source=access_source,
            ip_address=ip_address,
            device_hash=device_hash,
            user_agent=user_agent,
            expires_at=expires_at
        )

    @staticmethod
    def validate_and_use(token_str, client_ip, device_hash=None):
        """
        Validates token atomically and marks as used.
        Enforces IP lock + device hash binding [Spec §4.5].
        Token misuse triggers account freeze [Spec §4.5].
        """
        try:
            token = DownloadToken.objects.get(
                token=token_str,
                is_used=False,
                expires_at__gt=timezone.now()
            )
        except DownloadToken.DoesNotExist:
            raise ValueError("Invalid, expired, or already used token.")

        # IP binding check — misuse triggers freeze [Spec §4.5]
        if token.ip_address and token.ip_address != client_ip:
            DownloadManager._trigger_misuse_freeze(
                token.user, 'ip_mismatch',
                f'Token IP {token.ip_address} != request IP {client_ip}'
            )
            raise ValueError("IP address mismatch. Token locked to another device. Account flagged.")

        # Device hash binding check [Spec §4.5]
        if token.device_hash and device_hash and token.device_hash != device_hash:
            DownloadManager._trigger_misuse_freeze(
                token.user, 'device_mismatch',
                f'Token device {token.device_hash[:8]}... != request device {device_hash[:8]}...'
            )
            raise ValueError("Device fingerprint mismatch. Token locked to another device. Account flagged.")

        token.is_used = True
        token.save()
        return token

    @staticmethod
    def _trigger_misuse_freeze(profile, misuse_type, details):
        """
        Freeze account after token misuse [Spec §4.5, §4.6].
        Creates FraudAlert and freezes profile.
        """
        from apps.admin_panel.models import FraudAlert

        # Create fraud alert
        FraudAlert.objects.create(
            user=profile,
            alert_type='suspicious_activity',
            severity='high',
            details={'misuse_type': misuse_type, 'details': details},
            status='pending',
        )

        # Freeze account temporarily [Spec §4.6]
        profile.is_frozen = True
        profile.save(update_fields=['is_frozen'])

    @staticmethod
    def check_ip_attempts(ip_address, content_id, content_type, max_attempts=3):
        """
        Check if this IP has exceeded the download attempt limit [Spec §4.2].
        3 attempts per IP per content item.
        Returns remaining attempts for warning.
        """
        attempt, _ = DownloadAttempt.objects.get_or_create(
            ip_address=ip_address,
            content_id=content_id,
            content_type=content_type,
        )

        remaining = max_attempts - attempt.attempt_count

        if remaining <= 0:
            return False, f"Download attempt limit reached ({max_attempts}/{max_attempts}) for this IP.", 0

        # Warning at 1 attempt remaining [Spec §4.2]
        warning = None
        if remaining == 1:
            warning = "WARNING: This is your last download attempt for this content from this IP."

        return True, warning, remaining

    @staticmethod
    def increment_attempt(ip_address, content_id, content_type):
        """Increment the attempt counter for this IP + content."""
        attempt, _ = DownloadAttempt.objects.get_or_create(
            ip_address=ip_address,
            content_id=content_id,
            content_type=content_type,
        )
        attempt.attempt_count += 1
        attempt.save()
        return attempt.attempt_count

    @staticmethod
    def create_download_log(user, content_id, content_type, ip_address, device_hash=None, attempt_number=1):
        """Create a DownloadLog entry for audit [Spec P2 §6]."""
        return DownloadLog.objects.create(
            user=user,
            content_id=content_id,
            content_type=content_type,
            ip_address=ip_address,
            device_hash=device_hash,
            attempt_number=attempt_number,
        )

    @staticmethod
    def check_redownload_eligibility(profile, content_id, content_type):
        """
        Check if user needs to pay for re-download [Spec §4.3].
        - IP lock removed after 2 days
        - Must pay 50% of original price for re-download
        """
        from apps.commerce.models import Purchase

        purchase = Purchase.objects.filter(
            user=profile,
            content_id=content_id,
            content_type=content_type,
            is_revoked=False,
            download_completed=True,
            is_redownload=False,
        ).first()

        if not purchase:
            return False, "No completed purchase found."

        # Check for Download Insurance [Spec §4.3: Bypass lock and price]
        if hasattr(purchase, 'insurance') and purchase.insurance.status == 'active':
            return True, "Download Insurance active. Unlimited free re-downloads available."

        lock_expiry = purchase.created_at + timedelta(days=2)
        if timezone.now() < lock_expiry:
            return False, "Re-download lock active. Try again after 2 days from original purchase (or buy Download Insurance)."

        return True, "Re-download available at 50% price."

    @staticmethod
    def mark_download_complete(token, bytes_delivered, checksum_ok=True):
        """
        Mark a download as fully completed after byte + checksum verification [Spec §4.4].
        - Grace retry allowed if checksum fails.
        """
        token.download_completed = True
        token.bytes_delivered = bytes_delivered
        token.checksum_verified = checksum_ok
        token.save()

        # Mark purchase as download_completed ONLY if checksum is OK [Spec §4.4]
        if checksum_ok:
            from apps.commerce.models import Purchase
            Purchase.objects.filter(
                user=token.user,
                content_id=token.content_id,
                content_type=token.content_type,
                download_completed=False,
            ).order_by('-created_at').update(download_completed=True)

        # Update download log
        DownloadLog.objects.filter(
            user=token.user,
            content_id=token.content_id,
            content_type=token.content_type,
            completed=False,
        ).order_by('-created_at').update(completed=True, checksum_verified=checksum_ok, bytes_delivered=bytes_delivered)

    @staticmethod
    def check_ban_list(ip_address, device_hash=None):
        """Check if IP or device is banned [Spec §4.6]."""
        from apps.admin_panel.models import BanList

        if BanList.objects.filter(ban_type='ip', value=ip_address, is_active=True).exists():
            return True, "Your IP address has been banned."

        if device_hash and BanList.objects.filter(ban_type='device', value=device_hash, is_active=True).exists():
            return True, "Your device has been banned."

        return False, None
