from django.core.management.base import BaseCommand

from apps.commerce.payout_processor import process_weekly_payouts


class Command(BaseCommand):
    help = "Create payout records for every DJ whose available balance clears the threshold."

    def handle(self, *args, **options):
        result = process_weekly_payouts()
        self.stdout.write(self.style.SUCCESS(f"Payouts processed: {result['processed']}, failed: {result['failed']}"))
