from django.core.management.base import BaseCommand

from apps.commerce.escrow_utils import release_escrow_funds


class Command(BaseCommand):
    help = "Move sale earnings from escrow to available once the 24h/48h hold has passed."

    def handle(self, *args, **options):
        count, total = release_escrow_funds()
        self.stdout.write(self.style.SUCCESS(f"Released escrow for {count} purchase(s), total ₹{total}."))
