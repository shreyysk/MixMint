from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Check payouts still in flight with the payouts provider and send pending ones (automatic payouts)."

    def handle(self, *args, **opts):
        from apps.commerce.payout_gateway import active_provider, send_pending, sync_processing

        out = {"synced": sync_processing()}
        if active_provider():
            out["sent"] = send_pending()
        self.stdout.write(str(out))
