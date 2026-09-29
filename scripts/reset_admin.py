"""Remove every admin account on the LIVE site and create one new admin.
Run through scripts/reset_admin.ps1 (it loads the env file and asks for the password)."""
import os
from apps.accounts.models import User
from apps.accounts.validators import validate_strong_password
from django.db.models import Q

email = os.environ["NEW_ADMIN_EMAIL"].strip().lower()
password = os.environ["NEW_ADMIN_PASSWORD"]
validate_strong_password(password)  # stops here with a message if the password is too weak

admins = User.objects.filter(Q(is_superuser=True) | Q(is_staff=True) | Q(profile__role="admin")).distinct()
old = [u.email for u in admins if u.email.lower() != email]
User.objects.filter(email__in=old).delete()
print("Removed old admins:", ", ".join(old) or "none")

u = User.objects.filter(email__iexact=email).first() or User.objects.create_user(email=email)
u.is_staff = u.is_superuser = u.is_active = True
u.set_password(password)
u.save()
p = u.profile
p.role, p.is_banned, p.is_frozen = "admin", False, False
p.full_name = p.full_name or "Admin"
p.save()
print("New admin ready:", email)
