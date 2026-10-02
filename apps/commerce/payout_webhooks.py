"""Payout provider -> MixMint: transfer finished or failed. Verified by the provider's signature."""

import json
import logging

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .payout_gateway import PROVIDERS, apply_result

logger = logging.getLogger("mixmint")


def _handle(request, name):
    provider = PROVIDERS[name]
    raw = request.body or b""
    headers = {k.lower(): v for k, v in request.headers.items()}
    if not provider.verify_webhook(raw, headers):
        logger.warning("Rejected %s payout webhook with a bad signature", name)
        return HttpResponse(status=401)
    try:
        payload = json.loads(raw or b"{}")
    except ValueError:
        return HttpResponse(status=400)
    payout_id, result = provider.parse_webhook(payload)
    if payout_id:
        from .models import Payout

        if Payout.objects.filter(pk=payout_id, provider=name).exists():
            try:
                apply_result(payout_id, result)
            except Exception:
                logger.exception("Payout webhook %s for payout %s failed", name, payout_id)
                return HttpResponse(status=500)  # provider retries
    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
def cashfree_payout_webhook(request):
    return _handle(request, "cashfree")


@csrf_exempt
@require_POST
def razorpayx_payout_webhook(request):
    return _handle(request, "razorpayx")
