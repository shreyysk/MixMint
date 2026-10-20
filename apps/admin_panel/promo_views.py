"""Promo video endpoints: the DJ's promo page, the renderer's job links and the publish runner."""

import hmac
import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from . import promo
from .models import PromoVideo

logger = logging.getLogger("mixmint")


def _own(request, pk):
    profile = request.user.profile
    dj = getattr(profile, "dj_profile", None)
    pv = get_object_or_404(PromoVideo.objects.select_related("dj"), pk=pk)
    if dj is None or pv.dj_id != dj.pk:
        raise Http404
    return pv


@login_required
def promo_page(request, pk):
    pv = _own(request, pk)
    return render(request, "dashboard/promo.html", {
        "pv": pv, "tg_link": promo.tg_link(pv), "release_url": promo.item_url(pv),
        "video_url": promo.video_url(pv), "ig_max": promo.IG_MAX, "yt_max": promo.YT_MAX,
        "can_send": pv.status in ("waiting", "failed", "rejected"),
    })


@login_required
@require_POST
def promo_upload_url(request, pk):
    pv = _own(request, pk)
    from apps.core import r2

    try:
        data = json.loads(request.body or b"{}")
        return JsonResponse(promo.presign_raw(pv, data.get("filename", ""), data.get("size")))
    except (ValueError, r2.UploadError) as exc:
        return JsonResponse({"error": str(exc) or "Bad request."}, status=400)


@login_required
@require_POST
def promo_uploaded(request, pk):
    pv = _own(request, pk)
    from apps.core import r2

    try:
        data = json.loads(request.body or b"{}")
        promo.web_uploaded(pv, str(data.get("key") or ""))
    except (ValueError, r2.UploadError) as exc:
        return JsonResponse({"error": str(exc) or "Bad request."}, status=400)
    return JsonResponse({"ok": True, "status": pv.get_status_display()})


@login_required
def promo_status(request, pk):
    pv = _own(request, pk)
    return JsonResponse({"status": pv.status, "label": pv.get_status_display(), "video": promo.video_url(pv),
                         "ig": pv.ig_url, "yt": promo.yt_url(pv), "error": pv.error if pv.status == "failed" else ""})


# ── renderer (GitHub Actions) ──
def _job(request, pk):
    pv = PromoVideo.objects.filter(pk=pk).select_related("dj").first()
    if pv is None or not promo.check_job_token(pv, request.GET.get("t", "")):
        return None
    return pv


@csrf_exempt
@require_http_methods(["GET"])
def job_view(request, pk):
    pv = _job(request, pk)
    if pv is None:
        return JsonResponse({"error": "forbidden"}, status=403)
    if not pv.raw_key:
        return JsonResponse({"error": "no video"}, status=409)
    return JsonResponse(promo.job_info(pv))


@csrf_exempt
@require_POST
def job_done_view(request, pk):
    pv = _job(request, pk)
    if pv is None:
        return JsonResponse({"error": "forbidden"}, status=403)
    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        return HttpResponse(status=400)
    if pv.status not in ("rendering", "received", "failed"):
        return JsonResponse({"ok": True, "ignored": pv.status})
    promo.job_done(pv, data)
    return JsonResponse({"ok": True, "status": pv.status})


@csrf_exempt
@require_POST
def run_view(request):
    """MixMint → itself: post one approved video (signed, so only this site can start it)."""
    try:
        pid = int(json.loads(request.body or b"{}").get("id"))
    except (TypeError, ValueError):
        return HttpResponse(status=400)
    if not hmac.compare_digest(promo.run_sig(pid), request.headers.get("X-Promo-Sig", "")):
        return HttpResponse(status=403)
    pv = PromoVideo.objects.filter(pk=pid, status="posting").select_related("dj__profile").first()
    if pv is None:
        return JsonResponse({"ok": True, "skipped": True})
    return JsonResponse({"ok": True, "status": promo.publish(pv)})
