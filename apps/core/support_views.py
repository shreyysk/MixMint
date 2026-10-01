"""Help desk for buyers, DJs and guests: tickets + the Telegram bridge (see apps/admin_panel/support.py)."""

import json

from django.core.cache import cache
from django.core.validators import validate_email
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.admin_panel.models import SupportTicket
from apps.admin_panel.support import add_user_message, handle_update, open_ticket, webhook_secret
from apps.admin_panel.telegram import bot_deep_link
from apps.core.net import get_client_ip

CATEGORIES = ("order", "download", "payout", "dj_application", "account", "other")


def _limited(key, limit, seconds=3600):
    cache.add(key, 0, timeout=seconds)
    try:
        return cache.incr(key) > limit
    except ValueError:
        return False


@api_view(["POST"])
@permission_classes([AllowAny])
def create_support_ticket(request):
    """Ask the MixMint team a question. Logged-in users or guests (with an email).

    Body: {message | description, subject?, category?, email? (guests), name?}
    The admin gets a Telegram alert and can reply from Telegram or Admin → Support.
    """
    data = request.data
    if (data.get("website") or "").strip():  # honeypot field, invisible to people
        return Response({"message": "Thanks!"}, status=201)
    body = (data.get("message") or data.get("description") or "").strip()
    subject = (data.get("subject") or "").strip()
    category = (data.get("category") or "other").strip().lower()
    priority = (data.get("priority") or "medium").strip().lower()
    if len(body) < 5:
        return Response({"error": "Please write your question (a sentence or two)."}, status=400)
    user = request.user.profile if request.user.is_authenticated else None
    email = ""
    if user is None:
        email = (data.get("email") or "").strip().lower()
        try:
            validate_email(email)
        except Exception:
            return Response({"error": "Add your email so we can reply."}, status=400)
    who = f"u{request.user.pk}" if user else f"ip{get_client_ip(request)}"
    if _limited(f"support_tickets_{who}", 5 if user else 3):
        return Response({"error": "You've sent several questions recently. We'll get back to you soon."}, status=429)
    if category not in CATEGORIES:
        category = "other"
    if priority not in ("low", "medium", "high", "urgent"):
        priority = "medium"

    ticket = open_ticket(
        body=body, subject=subject, category=category, priority=priority, user=user, email=email,
        name=(data.get("name") or "").strip(), via="web",
    )
    return Response(
        {
            "id": ticket.id,
            "status": ticket.status,
            "telegram_url": bot_deep_link(f"ticket_{ticket.id}"),
            "message": "Sent ✓ We reply within a few hours"
            + (" — you'll see it here and by email." if user else f" by email to {email}."),
        },
        status=201,
    )


def _ticket_json(t):
    return {
        "id": t.id,
        "subject": t.subject,
        "category": t.category,
        "priority": t.priority,
        "status": t.status,
        "created_at": t.created_at.isoformat(),
        "updated_at": t.updated_at.isoformat(),
        "messages": [
            {"from": m.sender, "body": m.body, "at": m.created_at.isoformat()} for m in t.messages.all()
        ],
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_support_tickets(request):
    """My questions with the whole conversation (newest first)."""
    tickets = (
        SupportTicket.objects.filter(user=request.user.profile).prefetch_related("messages").order_by("-updated_at")[:20]
    )
    return Response([_ticket_json(t) for t in tickets])


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reply_support_ticket(request, ticket_id):
    ticket = SupportTicket.objects.filter(pk=ticket_id, user=request.user.profile).first()
    if ticket is None:
        return Response({"error": "Not found."}, status=404)
    body = (request.data.get("message") or "").strip()
    if len(body) < 2:
        return Response({"error": "Write a message first."}, status=400)
    if _limited(f"support_msgs_{request.user.pk}", 30):
        return Response({"error": "Too many messages. Please wait a bit."}, status=429)
    add_user_message(ticket, body, via="web")
    ticket.refresh_from_db()
    return Response(_ticket_json(ticket))


@csrf_exempt
@require_POST
def telegram_webhook(request):
    """Telegram → MixMint. Only Telegram knows the secret header we registered with setWebhook."""
    import hmac

    if not hmac.compare_digest(request.headers.get("X-Telegram-Bot-Api-Secret-Token", ""), webhook_secret()):
        return HttpResponse(status=403)
    try:
        update = json.loads(request.body or b"{}")
    except ValueError:
        return HttpResponse(status=400)
    try:
        handle_update(update)
    except Exception:
        import logging

        logging.getLogger("mixmint").exception("Telegram update failed")
    return JsonResponse({"ok": True})  # always 200 so Telegram doesn't retry forever


@csrf_exempt
@require_POST
def vault_callback(request):
    """Vault worker → MixMint: a copy to Telegram or a fetch back into R2 finished."""
    from apps.admin_panel import vault

    if not vault.verify_worker(request):
        return HttpResponse(status=403)
    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        return HttpResponse(status=400)
    return JsonResponse({"ok": vault.apply_worker_result(data)})


@csrf_exempt
@require_POST
def vault_run(request):
    """MixMint → itself: run one vault transfer (signed, so only this site can start one)."""
    from apps.admin_panel import mtproto, vault

    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        return HttpResponse(status=400)
    if not mtproto.check_signature(data, request.headers.get("X-Vault-Sig", "")):
        return HttpResponse(status=403)
    return JsonResponse(vault.run_job(data))
