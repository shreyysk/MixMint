import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from apps.tracks.models import Track

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Updates the sales_last_7_days field for all tracks based on purchases in the last 7 days.'

    def handle(self, *args, **options):
        since = timezone.now() - timedelta(days=7)

        # We count completed downloads with an active status in the last 7 days
        tracks = Track.objects.annotate(
            weekly_sales=Count(
                'purchases',
                filter=Q(
                    purchases__created_at__gte=since,
                    purchases__download_completed=True,
                    purchases__status='active'
                )
            )
        )

        updated_count = 0
        for track in tracks:
            # Only update and save if the count changed to minimize DB hits
            if track.sales_last_7_days != track.weekly_sales:
                track.sales_last_7_days = track.weekly_sales
                track.save(update_fields=['sales_last_7_days'])
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully updated weekly sales for {updated_count} tracks.'))
        logger.info(f"Cron update_weekly_sales completed: updated {updated_count} tracks.")
