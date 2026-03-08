import pyotp
from django.utils import timezone
from datetime import timedelta
from apps.admin_panel.email_utils import send_email

def generate_totp_secret():
    """Generates a new base32 TOTP secret."""
    return pyotp.random_base32()

def get_totp_uri(dj_profile):
    """Generates the provisioning URI for Google Authenticator/Authy."""
    if not dj_profile.payout_otp_secret:
        dj_profile.payout_otp_secret = generate_totp_secret()
        dj_profile.save(update_fields=['payout_otp_secret'])
    
    return pyotp.totp.TOTP(dj_profile.payout_otp_secret).provisioning_uri(
        name=dj_profile.profile.user.email,
        issuer_name="MixMint"
    )

def verify_totp(dj_profile, code):
    """Verifies a TOTP code."""
    if not dj_profile.payout_otp_secret:
        return False, "TOTP not configured."
    
    totp = pyotp.TOTP(dj_profile.payout_otp_secret)
    if totp.verify(code):
        return True, "Verified."
    return False, "Invalid verification code."

# Keep original for legacy/fallback if needed, but rename if appropriate.
# The spec says TOTP is required for payouts.
def verify_payout_otp(dj_profile, code):
    """
    Primary 2FA check for payouts [Fix 06].
    Checks TOTP (Google Authenticator).
    """
    return verify_totp(dj_profile, code)
