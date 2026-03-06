"""
Temporary Email Domain Blocklist — prevents disposable/spam email signups [Spec P2 §13].

This middleware intercepts signup requests and rejects known temporary email domains.
Also applied in the serializer layer for double enforcement.
"""

# Common disposable email domains — extend this list as needed
BLOCKED_EMAIL_DOMAINS = frozenset([
    'mailinator.com', 'guerrillamail.com', 'guerrillamail.net',
    'throwam.com', 'trashmail.com', 'trashmail.net', 'trashmail.org',
    'maildrop.cc', 'sharklasers.com', 'guerrillamailblock.com',
    'yopmail.com', 'yopmail.fr', 'cool.fr.nf', 'jetable.fr.nf',
    'nospam.ze.tc', 'nomail.xl.cx', 'mega.zik.dj', 'speed.1s.fr',
    'courriel.fr.nf', 'moncourrier.fr.nf', 'dispostable.com',
    'tempmail.com', 'temp-mail.org', 'temp-mail.io', 'tempinbox.com',
    'fakeinbox.com', 'mailnull.com', 'spamgourmet.com', 'spamgourmet.net',
    'mailnesia.com', 'mailnull.com', '10minutemail.com', '10minutemail.net',
    'getairmail.com', 'throwam.com', 'tempomail.fr', 'turual.com',
    'mailscrap.com', 'spaml.de', 'filzmail.com', 'wegwerfemail.de',
    'spamfree24.org', 'objectmail.com', 'deadaddress.com', 'mailexpire.com',
    'throwaway.email', 'anonaddy.com', 'simplelogin.io', 'discard.email',
])


def is_disposable_email(email: str) -> bool:
    """Return True if the email domain is in the blocklist."""
    if not email or '@' not in email:
        return False
    domain = email.split('@')[-1].lower().strip()
    return domain in BLOCKED_EMAIL_DOMAINS


def validate_email_domain(email: str):
    """
    Raises ValueError if email is from a blocked domain.
    Use in serializer validators.
    """
    if is_disposable_email(email):
        raise ValueError(
            "Disposable/temporary email addresses are not allowed on MixMint. "
            "Please use a real email address."
        )
