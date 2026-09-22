"""Buyer/DJ support: tickets + Telegram bridge."""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.admin_panel.models import SupportTicket
from apps.admin_panel.telegram import bot_deep_link, notify_support_ticket

CATEGORIES = ("order", "download", "payout", "dj_application", "account", "other")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_support_ticket(request):
    """File a support ticket. Also pings admins on Telegram (best-effort).

    Body: {subject, description, category?, priority?}
    Response includes the Telegram deep link for live chat.
    """
    subject = (request.data.get("subject") or "").strip()
    description = (request.data.get("description") or "").strip()
    category = (request.data.get("category") or "other").strip().lower()
    priority = (request.data.get("priority") or "medium").strip().lower()
    if not subject or not description:
        return Response({"error": "Subject and description are required."}, status=400)
    if category not in CATEGORIES:
        category = "other"
    if priority not in ("low", "medium", "high", "urgent"):
        priority = "medium"

    ticket = SupportTicket.objects.create(
        user=request.user.profile,
        subject=subject[:255],
        category=category,
        priority=priority,
        description=description,
    )
    telegram_sent = notify_support_ticket(ticket)
    return Response(
        {
            "id": ticket.id,
            "status": ticket.status,
            "telegram_url": bot_deep_link(f"ticket_{ticket.id}"),
            "telegram_sent": telegram_sent,
            "message": "Ticket received. We reply within 12–24 hours; urgent issues get fastest response on Telegram.",
        },
        status=201,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_support_tickets(request):
    """List my tickets (newest first)."""
    tickets = SupportTicket.objects.filter(user=request.user.profile).order_by("-created_at")[:50]
    return Response(
        [
            {
                "id": t.id,
                "subject": t.subject,
                "category": t.category,
                "priority": t.priority,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
            }
            for t in tickets
        ]
    )
