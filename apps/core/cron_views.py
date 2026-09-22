"""Secured cron endpoints for worker-free (free-tier) hosting.

On hosts like Render-free there is no always-on worker/beat. Instead, a free
external scheduler (e.g. cron-job.org) calls these URLs on a timetable:

    GET /cron/cleanup/        every 10 min  (tokens + external R2 cache)
    GET /cron/warm-cache/     every 30 min  (pre-cache Drive files to R2)
    GET /cron/weekly-sales/   daily 04:00   (sales_last_7_days)
    GET /cron/payout-cron/    daily 02:00   (renewals + overage billing)
    GET /cron/ad-floor/       weekly        (ad floor pricing)
    GET /cron/reset-quotas/   monthly       (quota resets)

Auth: ?secret=<CRON_SECRET> (constant-time compare). Never expose the secret
in logs — it travels as a query param over HTTPS only.
"""

import hmac
import logging

from django.conf import settings
from django.core.management import call_command
from django.http import JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger("mixmint")

JOBS = {
    "cleanup": ["cleanup_tokens"],
    "warm-cache": ["warm_external_cache"],
    "weekly-sales": ["update_weekly_sales"],
    "payout-cron": ["payout_cron"],
    "ad-floor": ["update_ad_floor_pricing"],
    "reset-quotas": ["reset_quotas"],
}


@require_GET
def run_cron_job(request, job):
    expected = getattr(settings, "CRON_SECRET", "") or ""
    provided = request.GET.get("secret", "") or request.headers.get("X-Cron-Secret", "")
    if not expected or not hmac.compare_digest(str(provided), str(expected)):
        return JsonResponse({"error": "Forbidden."}, status=403)
    if job not in JOBS:
        return JsonResponse({"error": "Unknown job.", "jobs": sorted(JOBS)}, status=404)
    ran = []
    try:
        for cmd in JOBS[job]:
            call_command(cmd)
            ran.append(cmd)
    except Exception as exc:
        logger.exception("Cron job %s failed.", job)
        return JsonResponse({"job": job, "ok": False, "error": str(exc)[:300]}, status=500)
    return JsonResponse({"job": job, "ok": True, "ran": ran})
