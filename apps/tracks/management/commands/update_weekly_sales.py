import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from apps.commerce.models import Purchase
from apps.tracks.models import Track

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Updates Track.sales_last_7_days from paid purchases in the last 7 days."

    def handle(self, *args, **options):
        since = timezone.now() - timedelta(days=7)
        counts = dict(
            Purchase.objects.filter(
                content_type="track",
                status="paid",
                is_redownload=False,
                is_revoked=False,
                created_at__gte=since,
            )
            .values_list("content_id")
            .annotate(n=Count("id"))
        )

        updated = 0
        # Reset tracks that no longer have recent sales.
        updated += (
            Track.objects.filter(sales_last_7_days__gt=0).exclude(id__in=counts.keys()).update(sales_last_7_days=0)
        )
        for track_id, n in counts.items():
            updated += Track.objects.filter(id=track_id).exclude(sales_last_7_days=n).update(sales_last_7_days=n)

        self.stdout.write(self.style.SUCCESS(f"Successfully updated weekly sales for {updated} tracks."))
        logger.info("Cron update_weekly_sales completed: updated %s tracks.", updated)
