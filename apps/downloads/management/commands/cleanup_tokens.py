from django.core.management.base import BaseCommand
from apps.downloads.models import DownloadToken
from django.utils import timezone


class Command(BaseCommand):
    help = "Clean up expired and used download tokens + temp-cached external files"

    def handle(self, *args, **options):
        now = timezone.now()
        # First remove temp cached files for stale external tokens (keep row for audit).
        stale_cached = DownloadToken.objects.filter(expires_at__lt=now).exclude(cached_file_path="")
        files_removed = 0
        for dl in stale_cached.iterator():
            import os

            try:
                if dl.cached_file_path and os.path.exists(dl.cached_file_path):
                    os.remove(dl.cached_file_path)
                    files_removed += 1
            except OSError:
                pass
            dl.cached_file_path = ""
            dl.save(update_fields=["cached_file_path"])
        # Then delete fully-expired plain tokens without cache (audit-preserving for cached ones).
        deleted, _ = DownloadToken.objects.filter(expires_at__lt=now, cached_file_path="").delete()
        self.stdout.write(
            self.style.SUCCESS(f"Successfully deleted {deleted} expired tokens, cleared {files_removed} cached file(s)")
        )
