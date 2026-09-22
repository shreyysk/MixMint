from celery.schedules import crontab
import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("mixmint")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


app.conf.beat_schedule = {
    "update-weekly-sales-every-monday": {
        "task": "apps.tracks.tasks.update_weekly_sales",
        "schedule": crontab(day_of_week="monday", hour=0, minute=0),
    },
    "cleanup-expired-tokens-daily": {
        "task": "apps.downloads.tasks.cleanup_expired_tokens",
        "schedule": crontab(hour=3, minute=0),
    },
    "reset-monthly-quotas": {
        "task": "apps.commerce.tasks.reset_monthly_quotas",
        "schedule": crontab(day_of_month=1, hour=0, minute=30),
    },
    "weekly-payout-processing": {
        "task": "apps.commerce.tasks.process_weekly_payouts",
        "schedule": crontab(day_of_week="friday", hour=18, minute=0),
    },
}
