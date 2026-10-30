"""Runs before every Railway deploy: apply migrations, then create the first admin if asked to.

The admin is created only when DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD are set and no
account with that email exists yet. An existing account is never changed, so the password variable
can be removed after the first deploy.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Migrate the database and create the first admin from DJANGO_SUPERUSER_EMAIL / DJANGO_SUPERUSER_PASSWORD."

    def handle(self, *args, **opts):
        call_command("migrate", interactive=False)
        email = (os.environ.get("DJANGO_SUPERUSER_EMAIL") or "").strip().lower()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD") or ""
        if not (email and password):
            self.stdout.write("predeploy: no admin requested")
            return
        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            self.stdout.write(f"predeploy: admin {email} already exists, left unchanged")
            return
        User.objects.create_superuser(email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"predeploy: created admin {email}"))
