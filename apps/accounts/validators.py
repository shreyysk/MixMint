"""
MixMint Validation Utilities [Spec §13].

Blocks temporary/disposable email domains and enforces
strong password requirements.
"""

from django.core.exceptions import ValidationError

# Common disposable email domains [Spec §13: Temporary emails blocked]
BLOCKED_EMAIL_DOMAINS = {
    'mailinator.com', 'guerrillamail.com', 'guerrillamail.net',
    'yopmail.com', 'tempmail.com', 'throwaway.email',
    'temp-mail.org', 'fakeinbox.com', 'sharklasers.com',
    'guerrillamailblock.com', 'grr.la', 'dispostable.com',
    'mailnesia.com', 'maildrop.cc', 'discard.email',
    'trashmail.com', 'trashmail.me', 'trashmail.net',
    'mytemp.email', 'tempail.com', 'mohmal.com',
    'getnada.com', 'emailondeck.com', 'incognitomail.com',
    'mailcatch.com', 'tmail.ws', 'tempr.email',
    'burnermail.io', 'harakirimail.com', 'spamgourmet.com',
    '10minutemail.com', 'minutemail.com', 'tempmailaddress.com',
    'throwawayemail.com', 'tmpmail.net', 'tmpmail.org',
    'bupmail.com', 'mailsac.com', 'emailfake.com',
    'crazymailing.com', 'armyspy.com', 'dayrep.com',
    'einrot.com', 'fleckens.hu', 'gustr.com',
    'jourrapide.com', 'rhyta.com', 'superrito.com',
    'teleworm.us',
}


def validate_email_domain(email):
    """
    Reject disposable/temporary email domains [Spec §13].
    Raises ValidationError if domain is blocked.
    """
    if not email or '@' not in email:
        raise ValidationError('Invalid email address.')

    domain = email.split('@')[1].lower()
    if domain in BLOCKED_EMAIL_DOMAINS:
        raise ValidationError(
            'Temporary email addresses are not allowed. '
            'Please use a permanent email address.'
        )


def validate_strong_password(password):
    """
    Enforce strong password requirements [Spec §11].
    """
    if len(password) < 8:
        raise ValidationError('Password must be at least 8 characters long.')

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)

    if not (has_upper and has_lower and has_digit and has_special):
        raise ValidationError(
            'Password must contain at least one uppercase letter, '
            'one lowercase letter, one digit, and one special character.'
        )
