"""
Start MixMint from zero: delete every row in the database (users, DJs, tracks, albums,
purchases, wallets, settings, sessions...) and, optionally, every file in the R2 buckets.
Tables and migrations are kept, so the site keeps working straight afterwards.

    python manage.py wipe_everything --database --storage --confirm DELETE-EVERYTHING --admin-email you@example.com

Or keep the admins, all settings and every R2 file, and delete only the other accounts:

    python manage.py wipe_everything --users --confirm DELETE-EVERYTHING

Safety:
  * nothing happens without --confirm DELETE-EVERYTHING
  * it shows which database / buckets it will empty and asks you to type "yes"
  * it saves a JSON backup of the database first (skip with --no-backup)

THIS CANNOT BE UNDONE (except by loading the backup with `python manage.py loaddata <file>`).
"""

import getpass
import os
from datetime import datetime

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

CONFIRM = "DELETE-EVERYTHING"


class Command(BaseCommand):
    help = "Permanently delete all data (and optionally all R2 files) so you can start fresh."

    def add_arguments(self, parser):
        parser.add_argument("--database", action="store_true", help="Delete every row in every table.")
        parser.add_argument("--storage", action="store_true", help="Delete every file in the R2 buckets.")
        parser.add_argument(
            "--users",
            action="store_true",
            help="Delete every account except admins (plus what those accounts own). Files and settings stay.",
        )
        parser.add_argument("--confirm", default="", help=f"Must be exactly {CONFIRM}.")
        parser.add_argument("--admin-email", default="", help="Create a new admin account afterwards.")
        parser.add_argument("--no-backup", action="store_true", help="Don't save a JSON backup first.")
        parser.add_argument("--yes", action="store_true", help="Skip the final typed 'yes' (for scripts).")

    def handle(self, *args, **opts):
        if not (opts["database"] or opts["storage"] or opts["users"]):
            raise CommandError("Nothing to do: add --users, --database and/or --storage.")
        if opts["users"] and opts["database"]:
            raise CommandError("Use --users OR --database, not both.")
        if opts["confirm"] != CONFIRM:
            raise CommandError(f"Refusing to delete anything. Add --confirm {CONFIRM} if you are sure.")

        db = settings.DATABASES["default"]
        self.stdout.write(self.style.WARNING("This will PERMANENTLY delete:"))
        if opts["database"]:
            self.stdout.write(f"  - every row in database {db.get('NAME')} on {db.get('HOST') or 'local file'}")
            self.stdout.write(f"    ({self._row_summary()})")
        if opts["storage"]:
            self.stdout.write(f"  - every file in R2 buckets: {', '.join(self._buckets())}")
        if opts["users"]:
            kept, doomed = self._split_users()
            self.stdout.write(f"  - {doomed.count()} accounts on {db.get('HOST') or 'local file'} ({self._owned_summary(doomed)})")
            self.stdout.write(f"  Keeping {kept.count()} admin account(s): {', '.join(kept.values_list('email', flat=True)) or 'NONE'}")
            self.stdout.write("  R2 files, platform settings and offers are NOT touched.")
            if not kept.exists() and not opts["admin_email"]:
                raise CommandError("There is no admin account to keep. Add --admin-email you@example.com.")
        if not opts["yes"] and input('Type "yes" to continue: ').strip().lower() != "yes":
            raise CommandError("Cancelled. Nothing was deleted.")

        if (opts["database"] or opts["users"]) and not opts["no_backup"]:
            self._backup()
        if opts["storage"]:
            self._wipe_storage()
        if opts["database"]:
            self.stdout.write("Deleting all database rows...")
            call_command("flush", interactive=False, verbosity=0)  # keeps tables + migrations
            from django.core.cache import cache

            try:
                cache.clear()  # cached settings, rate-limit counters, fraud counters
            except Exception:
                pass
            self.stdout.write(self.style.SUCCESS("Database is empty."))

        if opts["users"]:
            _, doomed = self._split_users()
            n = doomed.count()
            doomed.delete()  # cascades to profiles, DJ profiles, tracks, albums, purchases, wallets...
            from django.contrib.sessions.models import Session
            from django.core.cache import cache

            Session.objects.all().delete()  # everyone (admins too) logs in again
            try:
                cache.clear()
            except Exception:
                pass
            self.stdout.write(self.style.SUCCESS(f"Deleted {n} accounts. Admin accounts kept."))

        if opts["admin_email"]:
            self._create_admin(opts["admin_email"].strip().lower())
        self.stdout.write(self.style.SUCCESS("Done. MixMint is a clean slate."))

    # ------------------------------------------------------------------ helpers
    def _split_users(self):
        from django.contrib.auth import get_user_model
        from django.db.models import Q

        User = get_user_model()
        is_admin = Q(is_superuser=True) | Q(is_staff=True) | Q(profile__role="admin")
        return User.objects.filter(is_admin).distinct(), User.objects.exclude(is_admin)

    def _owned_summary(self, users):
        try:
            from apps.albums.models import AlbumPack
            from apps.commerce.models import Purchase
            from apps.tracks.models import Track

            return (
                f"their {Track.objects.filter(dj__profile__user__in=users).count()} tracks, "
                f"{AlbumPack.objects.filter(dj__profile__user__in=users).count()} albums and "
                f"{Purchase.objects.filter(user__user__in=users).count()} purchases go with them"
            )
        except Exception as exc:
            return f"could not count: {exc}"

    def _row_summary(self):
        try:
            from apps.accounts.models import User
            from apps.albums.models import AlbumPack
            from apps.commerce.models import Purchase
            from apps.tracks.models import Track

            return (
                f"{User.objects.count()} users, {Track.objects.count()} tracks, "
                f"{AlbumPack.objects.count()} albums, {Purchase.objects.count()} purchases"
            )
        except Exception as exc:
            return f"could not count rows: {exc}"

    def _backup(self):
        path = os.path.abspath(f"mixmint-backup-{datetime.now():%Y%m%d-%H%M%S}.json")
        self.stdout.write(f"Saving a backup to {path} ...")
        with open(path, "w", encoding="utf-8") as fh:
            call_command(
                "dumpdata",
                natural_foreign=True,
                natural_primary=True,
                exclude=["contenttypes", "auth.permission", "sessions", "admin.logentry"],
                stdout=fh,
                verbosity=0,
            )
        self.stdout.write(self.style.SUCCESS(f"Backup saved ({os.path.getsize(path) // 1024} KB). Keep it private."))

    def _buckets(self):
        return sorted(b for b in {settings.R2_PRIVATE_BUCKET, getattr(settings, "R2_PUBLIC_BUCKET", "")} if b)

    def _wipe_storage(self):
        import boto3
        from botocore.config import Config

        s3 = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )
        for bucket in self._buckets():
            deleted = 0
            try:
                paginator = s3.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=bucket):
                    keys = [{"Key": o["Key"]} for o in page.get("Contents", [])]
                    if keys:
                        s3.delete_objects(Bucket=bucket, Delete={"Objects": keys, "Quiet": True})
                        deleted += len(keys)
            except Exception as exc:
                code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
                if code == "NoSuchBucket":
                    self.stdout.write(f"  {bucket}: bucket doesn't exist, skipped")
                    continue
                raise CommandError(f"Could not empty {bucket}: {exc}")
            self.stdout.write(self.style.SUCCESS(f"  {bucket}: deleted {deleted} files"))

    def _create_admin(self, email):
        from django.contrib.auth import get_user_model

        from apps.accounts.validators import validate_strong_password

        while True:
            pw = getpass.getpass(f"New password for admin {email}: ")
            if pw != getpass.getpass("Type it again: "):
                self.stdout.write(self.style.ERROR("Passwords don't match, try again."))
                continue
            try:
                validate_strong_password(pw)
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(getattr(e, "message", str(e))))
        existing = get_user_model().objects.filter(email__iexact=email).first()
        if existing:
            existing.set_password(pw)
            existing.is_staff = existing.is_superuser = True
            existing.save()
            user = existing
        else:
            user = get_user_model().objects.create_superuser(email=email, password=pw)
        profile = user.profile
        profile.role = "admin"
        profile.full_name = profile.full_name or "Admin"
        profile.save()
        self.stdout.write(self.style.SUCCESS(f"Admin account created: {email}"))
