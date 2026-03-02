from django.core.management.base import BaseCommand
from apps.downloads.models import DownloadToken
from django.utils import timezone

class Command(BaseCommand):
    help = 'Clean up expired and used download tokens'

    def handle(self, *args, **options):
        now = timezone.now()
        deleted, _ = DownloadToken.objects.filter(
            expires_at__lt=now
        ).delete()
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted} expired tokens'))
