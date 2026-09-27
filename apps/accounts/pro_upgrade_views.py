"""
Pro DJ upgrade view [Spec P3 §1.5].

Endpoint: POST /api/v1/accounts/dj/upgrade-pro/
- Creates a payment order for the Pro subscription fee.
- On payment verification, sets is_pro_dj=True on the Profile,
  unlocking 8% commission and custom domain.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from apps.accounts.models import DJProfile

# Pro Plan pricing
PRO_PLAN_PRICE_PAISE = 99900  # ₹999 in paise
PRO_PLAN_PRICE_INR = 999.00
PRO_MONTHLY_PRICE_PAISE = 14900  # ₹149 in paise


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upgrade_to_pro(request):
    """
    Initiate a Pro DJ upgrade order [Spec P3 §1.5].

    Creates a payment order for the annual Pro subscription.
    After verified payment:
    - Profile.is_pro_dj = True
    - Commission drops from 15% → 8%
    - Custom domain and ad reduction features unlocked
    """
    profile = request.user.profile

    # Must be an approved DJ
    if profile.role != "dj":
        return Response({"error": "Only approved DJs can upgrade to Pro."}, status=status.HTTP_403_FORBIDDEN)

    try:
        dj_profile = profile.dj_profile
    except DJProfile.DoesNotExist:
        return Response({"error": "DJ profile not found."}, status=status.HTTP_404_NOT_FOUND)

    if dj_profile.status != "approved":
        return Response(
            {"error": "Your DJ application must be approved before upgrading."}, status=status.HTTP_400_BAD_REQUEST
        )

    # Already Pro?
    if profile.is_pro_dj:
        return Response({"message": "You are already a Pro DJ.", "is_pro_dj": True}, status=status.HTTP_200_OK)

    plan_type = request.data.get("plan_type", "annual")
    if plan_type not in ("annual", "monthly"):
        plan_type = "annual"
    amount_paise = PRO_PLAN_PRICE_PAISE if plan_type == "annual" else PRO_MONTHLY_PRICE_PAISE

    from apps.commerce.models import ProSubscriptionEvent
    from apps.payments.utils import get_gateway
    from apps.payments.views import _gateway_payload

    try:
        gateway = get_gateway(request.data.get("gateway"))
        result = gateway.create_subscription_order(
            dj_id=str(dj_profile.id), plan_type=plan_type, amount_paise=amount_paise
        )
    except Exception:
        import logging

        logging.getLogger("mixmint").exception("Pro upgrade order failed for DJ %s", dj_profile.id)
        return Response(
            {"error": "Failed to create payment order. Please try again."}, status=status.HTTP_502_BAD_GATEWAY
        )
    order_id = result.get("gateway_order_id") or result.get("order_id")
    # Activation happens only when the gateway confirms payment (apps.payments.services).
    ProSubscriptionEvent.objects.create(
        dj=dj_profile,
        event_type="payment_initiated",
        plan_type=plan_type,
        amount_paise=amount_paise,
        gateway=gateway.name,
        gateway_order_id=order_id,
    )

    payload = _gateway_payload(result, order_id, amount_paise)
    payload.update(
        {
            "amount_inr": amount_paise / 100,
            "plan_type": plan_type,
            "description": f"MixMint Pro ({plan_type})",
            "message": f"Complete ₹{amount_paise / 100:.0f} payment to activate Pro DJ.",
            "features": [
                "8% platform commission (vs 15% standard)",
                "Custom domain support (e.g. music.yourname.com)",
                "Reduced ad exposure for your storefront",
                "Priority support",
            ],
        }
    )
    return Response(payload, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def admin_grant_pro(request, dj_profile_id):
    """
    Admin manually grants Pro DJ status [Spec P3 §1.5].
    Use for comped upgrades, influencer partnerships, etc.
    """
    try:
        dj_profile = DJProfile.objects.get(id=dj_profile_id, status="approved")
    except DJProfile.DoesNotExist:
        return Response({"error": "Approved DJ profile not found."}, status=status.HTTP_404_NOT_FOUND)

    profile = dj_profile.profile
    profile.is_pro_dj = True
    profile.save(update_fields=["is_pro_dj"])

    return Response(
        {
            "status": "pro_granted",
            "message": f"{dj_profile.dj_name} is now a Pro DJ (8% commission, custom domain).",
            "dj_profile_id": dj_profile.id,
        }
    )
