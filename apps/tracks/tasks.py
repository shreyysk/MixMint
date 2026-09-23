from celery import shared_task
from django.core.management import call_command


@shared_task
def update_weekly_sales():
    """Weekly task to update sales_last_7_days for tracks [BUG-14]."""
    call_command("update_weekly_sales")
    return "Weekly sales updated successfully."


@shared_task
def detect_offload_candidates():
    """Weekly offload-candidate detection (beat entry for the management command)."""
    call_command("detect_offload_candidates")
    return "Offload candidates detected."
