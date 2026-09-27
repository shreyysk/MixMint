"""Turns Google sign-in errors into a friendly message on the login page instead of a 500."""

import logging

from social_core import exceptions as sx
from social_django.middleware import SocialAuthExceptionMiddleware

logger = logging.getLogger("mixmint")


class MixMintSocialAuthExceptionMiddleware(SocialAuthExceptionMiddleware):
    def raise_exception(self, request, exception):
        return False  # never show a stack trace / 500 for a sign-in problem

    def get_message(self, request, exception):
        if isinstance(exception, sx.AuthCanceled):
            return "Google sign-in was cancelled."
        if isinstance(exception, (sx.AuthStateMissing, sx.AuthStateForbidden, sx.AuthMissingParameter)):
            return "Your Google sign-in timed out. Please try again."
        if isinstance(exception, sx.AuthAlreadyAssociated):
            return "That Google account is already linked to a different MixMint account."
        if isinstance(exception, sx.AuthForbidden):
            return str(exception) if type(exception) is not sx.AuthForbidden else "This account can't sign in."
        logger.warning("Google sign-in failed: %r", exception)
        return "Google sign-in failed. Please try again or use email and password."

    def get_redirect_uri(self, request, exception):
        return "/login/"
