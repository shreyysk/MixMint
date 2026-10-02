"""
Custom steps for the Google sign-in pipeline (python-social-auth).

Order (see SOCIAL_AUTH_PIPELINE in settings):
    ... social_user
    require_verified_email      refuse Google accounts whose email Google hasn't verified
    associate_by_verified_email link to an existing MixMint account with the same email
    ... create_user / associate_user / user_details
    finish_mixmint_login        profile name, referral, frozen/banned check, login history
"""

import logging

from social_core.exceptions import AuthForbidden

logger = logging.getLogger("mixmint")


class AccountRestricted(AuthForbidden):
    """Shown to the user by SocialAuthExceptionMiddleware as a login-page message."""

    def __init__(self, backend, message):
        super().__init__(backend)
        self.message = message

    def __str__(self):
        return self.message


def _email(details, response):
    return ((details or {}).get("email") or (response or {}).get("email") or "").strip().lower()


def require_verified_email(backend, details, response, *args, **kwargs):
    email = _email(details, response)
    if not email:
        raise AccountRestricted(backend, "Your Google account didn't share an email address. Please try again.")
    verified = (response or {}).get("email_verified", (response or {}).get("verified_email", True))
    if verified in (False, "false", "False"):
        raise AccountRestricted(backend, "Please verify your email with Google first, then try again.")
    details["email"] = email
    return {"details": details}


def associate_by_verified_email(backend, details, response, user=None, *args, **kwargs):
    """
    Someone who signed up with email + password can later use "Continue with Google"
    for the same address. Safe because require_verified_email ran first.
    """
    if user:
        return None
    from django.contrib.auth import get_user_model

    email = _email(details, response)
    match = get_user_model().objects.filter(email__iexact=email).first() if email else None
    if match:
        return {"user": match, "is_new": False}
    return None


def finish_mixmint_login(strategy, backend, user=None, is_new=False, details=None, *args, **kwargs):
    if user is None:
        return None
    from .models import LoginHistory, Profile

    request = strategy.request
    details = details or {}
    try:
        profile = user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=user, full_name=user.email)

    if not user.is_active or profile.is_banned:
        raise AccountRestricted(backend, "This account has been banned. Contact support if you think this is a mistake.")
    if profile.is_frozen:
        raise AccountRestricted(backend, "Your account has been frozen. Contact support.")

    changed = []
    google_name = (details.get("fullname") or "").strip() or " ".join(
        p for p in (details.get("first_name"), details.get("last_name")) if p
    ).strip()
    if google_name and (not profile.full_name or profile.full_name == user.email):
        profile.full_name = google_name[:120]
        changed.append("full_name")

    if is_new and request is not None:
        ref_code = request.session.get("ref_code")
        if ref_code and not profile.referred_by_id:
            from .models import AmbassadorCode

            ambassador = AmbassadorCode.objects.filter(code=ref_code, is_active=True).first()
            from apps.commerce.referrals import has_room

            if ambassador and has_room(ambassador.dj):
                profile.referred_by = ambassador.dj
                changed.append("referred_by")
                AmbassadorCode.objects.filter(pk=ambassador.pk).update(referral_count=ambassador.referral_count + 1)
            request.session.pop("ref_code", None)
    if changed:
        profile.save(update_fields=changed)

    if request is not None:
        from .frontend_views import _bind_session, _get_client_ip

        _bind_session(request)
        try:
            LoginHistory.objects.create(
                user=user,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
                location_data={"method": "google"},
            )
        except Exception:
            logger.exception("Could not record Google login history for user %s", user.pk)

    if is_new:
        from .frontend_views import _send_welcome

        _send_welcome(user)
    return None
