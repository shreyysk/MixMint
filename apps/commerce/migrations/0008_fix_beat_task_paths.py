# Fix 0007: its PeriodicTask rows pointed at management-command import paths
# (e.g. "apps.commerce.management.commands.payout_cron.Command.handle"),
# which are not Celery tasks — beat crashed resolving them on every tick.
# Point them at the real @shared_task wrappers instead.

from django.db import migrations

TASK_FIXES = {
    "Process Pro renewals and storage overage": "apps.commerce.tasks.run_payout_cron",
    "Cleanup expired download tokens": "apps.downloads.tasks.cleanup_expired_tokens",
    "Update weekly sales for tracks": "apps.tracks.tasks.update_weekly_sales",
    "Detect offload candidates": "apps.tracks.tasks.detect_offload_candidates",
}


def fix_task_paths(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    for name, task_path in TASK_FIXES.items():
        PeriodicTask.objects.filter(name=name).update(task=task_path)


defnoop = migrations.RunPython.noop


class Migration(migrations.Migration):

    dependencies = [
        ("commerce", "0007_add_periodic_tasks"),
    ]

    operations = [
        migrations.RunPython(fix_task_paths, defnoop),
    ]
