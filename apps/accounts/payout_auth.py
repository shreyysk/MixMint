import pyotp


def generate_totp_secret():
    """Generates a new base32 TOTP secret."""
    return pyotp.random_base32()


def get_totp_uri(dj_profile):
    """Generates the provisioning URI for Google Authenticator/Authy."""
    if not dj_profile.payout_otp_secret:
        dj_profile.payout_otp_secret = generate_totp_secret()
        dj_profile.save(update_fields=["payout_otp_secret"])

    return pyotp.totp.TOTP(dj_profile.payout_otp_secret).provisioning_uri(
        name=dj_profile.profile.user.email, issuer_name="MixMint"
    )


def verify_totp(dj_profile, code):
    """Verifies a TOTP code."""
    if not dj_profile.payout_otp_secret:
        return False, "TOTP not configured."

    code = str(code or "").strip()
    if not code.isdigit() or len(code) != 6:
        return False, "Enter the 6-digit code from your authenticator app."

    from django.core.cache import cache

    # Brute-force guard: 5 wrong codes -> 15 minute lockout.
    fail_key = f"totp_fail_{dj_profile.pk}"
    if cache.get(fail_key, 0) >= 5:
        return False, "Too many incorrect codes. Try again in 15 minutes."

    totp = pyotp.TOTP(dj_profile.payout_otp_secret)
    if not totp.verify(code, valid_window=1):
        cache.set(fail_key, cache.get(fail_key, 0) + 1, timeout=900)
        return False, "Invalid verification code."

    # Replay guard: a code can be used once.
    if not cache.add(f"totp_used_{dj_profile.pk}_{code}", 1, timeout=90):
        return False, "This code was already used. Wait for the next one."
    cache.delete(fail_key)
    return True, "Verified."


# Keep original for legacy/fallback if needed, but rename if appropriate.
# The spec says TOTP is required for payouts.


def verify_payout_otp(dj_profile, code):
    """
    Primary 2FA check for payouts [Fix 06].
    Checks TOTP (Google Authenticator).
    """
    return verify_totp(dj_profile, code)
