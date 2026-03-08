from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from apps.accounts.models import DJProfile, DJPageView

class Command(BaseCommand):
    help = 'Missing Item 02: Calculates dynamic ad floor CPM for DJs based on weekly page views.'

    def handle(self, *args, **kwargs):
        self.stdout.write('Calculating dynamic ad floor CPM...')
        
        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)

        djs = DJProfile.objects.filter(status='approved')
        updated_count = 0

        for dj in djs:
            views_last_7_days = DJPageView.objects.filter(
                dj=dj,
                created_at__gte=seven_days_ago
            ).count()

            # Dynamic Ad Floor CPM Logic
            base_cpm = Decimal('50.00')
            new_cpm = base_cpm
            
            if views_last_7_days > 10000:
                new_cpm = Decimal('250.00')
            elif views_last_7_days > 5000:
                new_cpm = Decimal('150.00')
            elif views_last_7_days > 1000:
                new_cpm = Decimal('100.00')
            elif views_last_7_days > 500:
                new_cpm = Decimal('75.00')

            # Update if changed or views changed
            if dj.weekly_views != views_last_7_days or dj.ad_floor_cpm != new_cpm:
                dj.weekly_views = views_last_7_days
                dj.ad_floor_cpm = new_cpm
                dj.save(update_fields=['weekly_views', 'ad_floor_cpm'])
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully updated ad floor CRM for {updated_count} DJs.'))
