from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from django.conf import settings
from apps.tracks.models import Track
from apps.albums.models import AlbumPack
from apps.commerce.models import OffloadNotification

# Phase 3 Configuration — these could be moved to settings or dynamic admin config
# For now, default values from the specification are used.
UNDERPERFORM_ZERO_SALES_DAYS = 60
UNDERPERFORM_LOW_SALES_COUNT = 2
UNDERPERFORM_LOW_SALES_PERIOD_DAYS = 90
MIN_AGE_DAYS_PAID = 30
MIN_AGE_DAYS_FREE = 7

class Command(BaseCommand):
    help = 'Phase 3 Feature 1: Detect underperforming tracks and free tracks on R2, notify DJs to offload to external link'

    def handle(self, *args, **kwargs):
        self.stdout.write('Detecting offload candidates...')

        cutoff_zero = timezone.now() - timedelta(days=UNDERPERFORM_ZERO_SALES_DAYS)
        cutoff_low = timezone.now() - timedelta(days=UNDERPERFORM_LOW_SALES_PERIOD_DAYS)
        too_new_paid = timezone.now() - timedelta(days=MIN_AGE_DAYS_PAID)
        too_new_free = timezone.now() - timedelta(days=MIN_AGE_DAYS_FREE)

        # --- 1. PAID UNDERPERFORMING ---
        # Tracks
        paid_tracks = Track.objects.filter(
            is_active=True,
            is_deleted=False,
            is_external_link=False,
            price__gt=0,
            created_at__lt=too_new_paid
        ).annotate(
            sales_in_period=Count(
                'purchases',
                filter=Q(
                    purchases__created_at__gte=cutoff_low,
                    purchases__download_completed=True,
                    purchases__status='active'
                )
            )
        ).filter(
            Q(sales_in_period=0) |
            Q(sales_in_period__lt=UNDERPERFORM_LOW_SALES_COUNT)
        )

        # Albums
        paid_albums = AlbumPack.objects.filter(
            is_active=True,
            is_deleted=False,
            is_external_link=False,
            price__gt=0,
            created_at__lt=too_new_paid
        ).annotate(
            sales_in_period=Count(
                'purchases',
                filter=Q(
                    purchases__created_at__gte=cutoff_low,
                    purchases__download_completed=True,
                    purchases__status='active'
                )
            )
        ).filter(
            Q(sales_in_period=0) |
            Q(sales_in_period__lt=UNDERPERFORM_LOW_SALES_COUNT)
        )

        # --- 2. FREE TRACKS ON R2 ---
        free_tracks = Track.objects.filter(
            is_active=True,
            is_deleted=False,
            is_external_link=False,
            price=0,
            created_at__lt=too_new_free
        )

        free_albums = AlbumPack.objects.filter(
            is_active=True,
            is_deleted=False,
            is_external_link=False,
            price=0,
            created_at__lt=too_new_free
        )

        all_candidates = list(paid_tracks) + list(paid_albums) + list(free_tracks) + list(free_albums)
        notified_djs = set()
        created_count = 0

        for content in all_candidates:
            # Avoid repeat spam within 30 days
            already_notified = OffloadNotification.objects.filter(
                content_id=content.id,
                created_at__gte=timezone.now() - timedelta(days=30)
            ).exists()

            if already_notified:
                continue

            content_type = 'track' if isinstance(content, Track) else 'album'
            reason = 'free_on_r2' if content.price == 0 else 'underperforming'
            storage_mb = (content.file_size or 0) // (1024 * 1024)

            sales = getattr(content, 'sales_in_period', None)
            
            OffloadNotification.objects.create(
                dj_id=content.dj_id,
                content_id=content.id,
                content_type=content_type,
                reason=reason,
                storage_mb=storage_mb,
                sales_in_period=sales,
                period_days=UNDERPERFORM_LOW_SALES_PERIOD_DAYS if reason == 'underperforming' else None
            )

            notified_djs.add(content.dj_id)
            created_count += 1

        # NOTE: Email sending logic should be implemented via Celery or bulk send 
        # in a production environment: `send_offload_digest_email(dj_id)`
        
        self.stdout.write(self.style.SUCCESS(f'Successfully found {created_count} candidates and queued for {len(notified_djs)} DJs.'))
