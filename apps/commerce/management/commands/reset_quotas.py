from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "No-op kept for the cron schedule: quotas/subscriptions were removed in Master Document v2.0."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Nothing to reset (subscriptions removed in v2.0)."))
