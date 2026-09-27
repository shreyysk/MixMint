from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm


class MixMintPasswordResetForm(PasswordResetForm):
    """
    Django's default skips accounts without a usable password, so people who joined
    with Google got no email at all. Proving they own the inbox is enough to let them
    set a password, so include them. Frozen/banned accounts are skipped.
    """

    def get_users(self, email):
        users = get_user_model()._default_manager.filter(email__iexact=(email or "").strip(), is_active=True)
        for user in users:
            profile = getattr(user, "profile", None)
            if profile is not None and (profile.is_banned or profile.is_frozen):
                continue
            yield user
