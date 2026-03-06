"""
MixMint Payout 2FA Authentication [Spec P2 §11, P3 §3.2].

Handles OTP generation and verification for DJ payout requests.
Uses email-based delivery via Resend.
"""

import random
import string
from django.utils import timezone
from datetime import timedelta
from apps.admin_panel.email_utils import send_email

def generate_payout_otp(dj_profile):
    """
    Generate a 6-digit OTP for payout verification.
    Valid for 10 minutes.
    """
    otp = ''.join(random.choices(string.digits, k=6))
    dj_profile.payout_otp_secret = otp
    dj_profile.payout_otp_timestamp = timezone.now()
    dj_profile.save(update_fields=['payout_otp_secret', 'payout_otp_timestamp'])
    
    send_email(
        to_email=dj_profile.profile.user.email,
        subject="MixMint Payout Verification Code",
        html_content=(
            f"<p>Your verification code for initiating a payout is:</p>"
            f"<h2>{otp}</h2>"
            f"<p>This code expires in 10 minutes.</p>"
        ),
    )
    return otp

def verify_payout_otp(dj_profile, user_otp):
    """
    Verify the provided OTP against the stored secret.
    Checks for expiration (10 minutes).
    """
    if not dj_profile.payout_otp_secret or not dj_profile.payout_otp_timestamp:
        return False, "No OTP generated."
    
    # Check expiration
    expiry_time = dj_profile.payout_otp_timestamp + timedelta(minutes=10)
    if timezone.now() > expiry_time:
        return False, "OTP has expired."
    
    if dj_profile.payout_otp_secret == user_otp:
        # Clear OTP after successful verification
        dj_profile.payout_otp_secret = None
        dj_profile.payout_otp_timestamp = None
        dj_profile.save(update_fields=['payout_otp_secret', 'payout_otp_timestamp'])
        return True, "Verified."
    
    return False, "Invalid OTP."
