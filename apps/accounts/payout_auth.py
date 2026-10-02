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


# ───────────────────────── Email codes (used for payouts) ─────────────────────────
# A 6-digit code is emailed to the DJ's login address before a withdrawal or a change of payout
# details. Codes last 10 minutes, work once, and 5 wrong tries lock it for 15 minutes.
CODE_TTL = 600


def _code_key(dj_profile):
    return f"payout_email_code_{dj_profile.pk}"


def send_payout_code(dj_profile, purpose="withdraw"):
    """Email a fresh code. Returns (ok, message)."""
    import hashlib
    import secrets

    from django.core.cache import cache
    from django.utils.html import escape

    if not cache.add(f"payout_code_sent_{dj_profile.pk}", 1, timeout=60):
        return False, "We just sent a code. Wait a minute before asking for another."
    hourly = f"payout_code_hour_{dj_profile.pk}"
    if cache.get(hourly, 0) >= 6:
        return False, "Too many codes requested. Try again in an hour."
    cache.set(hourly, cache.get(hourly, 0) + 1, timeout=3600)

    code = f"{secrets.randbelow(1_000_000):06d}"
    cache.set(_code_key(dj_profile), {"h": hashlib.sha256(code.encode()).hexdigest(), "p": purpose}, timeout=CODE_TTL)
    what = "withdraw your MixMint earnings" if purpose == "withdraw" else "change where your MixMint earnings are paid"
    email = dj_profile.profile.user.email
    try:
        from apps.admin_panel.email_utils import send_email

        send_email(
            email,
            f"Your MixMint code: {code}",
            f"<p>Use this code to {escape(what)}:</p>"
            f"<p style='font-size:28px;font-weight:700;letter-spacing:6px;font-family:monospace'>{code}</p>"
            "<p style='color:#666;font-size:13px'>It works once and expires in 10 minutes. "
            "If you didn't ask for it, someone may know your password: change it and contact MixMint support.</p>",
        )
    except Exception:
        cache.delete(_code_key(dj_profile))
        return False, "We couldn't send the email. Try again in a minute."
    shown = email[:2] + "•••" + email[email.index("@"):] if "@" in email else email
    return True, f"Code sent to {shown}. It works for 10 minutes."


def verify_email_code(dj_profile, code, purpose="withdraw"):
    import hashlib

    from django.core.cache import cache

    code = str(code or "").strip()
    if not code.isdigit() or len(code) != 6:
        return False, "Enter the 6-digit code from the email."
    fail_key = f"payout_code_fail_{dj_profile.pk}"
    if cache.get(fail_key, 0) >= 5:
        return False, "Too many incorrect codes. Try again in 15 minutes."
    saved = cache.get(_code_key(dj_profile))
    if not saved or saved.get("p") != purpose:
        return False, "That code has expired. Ask for a new one."
    if hashlib.sha256(code.encode()).hexdigest() != saved.get("h"):
        cache.set(fail_key, cache.get(fail_key, 0) + 1, timeout=900)
        return False, "That code isn't right. Check the email and try again."
    cache.delete(_code_key(dj_profile))  # single use
    cache.delete(fail_key)
    return True, "Verified."


def verify_payout_otp(dj_profile, code):
    """Withdrawals are confirmed with an emailed code (replaces the authenticator app)."""
    return verify_email_code(dj_profile, code, "withdraw")
