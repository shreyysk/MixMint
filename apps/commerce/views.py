from django.shortcuts import render
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from .models import Purchase, DJWallet, ProSubscriptionEvent, RefundRequest, Cart, CartItem
from .serializers import PurchaseSerializer, DJWalletSerializer, CartSerializer
import logging

logger = logging.getLogger(__name__)


class PurchaseViewSet(viewsets.ReadOnlyModelViewSet):
    """User's purchase history — only completed purchases [Spec §3.1]."""

    queryset = Purchase.objects.all()
    serializer_class = PurchaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Purchase.objects.filter(
            user=self.request.user.profile,
            status="paid",
        ).order_by("-created_at")


class DJWalletViewSet(viewsets.ReadOnlyModelViewSet):
    """DJ earnings wallet — DJs only [Spec §3.2]."""

    queryset = DJWallet.objects.all()
    serializer_class = DJWalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.profile.role != "dj":
            return DJWallet.objects.none()
        try:
            dj_profile = self.request.user.profile.dj_profile
            return DJWallet.objects.filter(dj=dj_profile)
        except Exception:
            return DJWallet.objects.none()


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def request_manual_payout(request):
    """
    DJ manually initiates a payout [Spec P2 §11, P3 §3.2].
    Requires 2FA verification code.
    """
    if request.user.profile.role != "dj" or not hasattr(request.user.profile, "dj_profile"):
        return Response({"error": "Only DJs can request payouts."}, status=status.HTTP_403_FORBIDDEN)

    code = request.data.get("verification_code")
    if not code:
        return Response({"error": "Verification code (OTP) is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        dj_profile = request.user.profile.dj_profile
        wallet = dj_profile.wallet
    except Exception:
        return Response({"error": "DJ profile or wallet not found."}, status=status.HTTP_404_NOT_FOUND)

    # Payouts are UPI/bank only. DJ must have UPI ID or bank account + IFSC saved.
    has_upi = bool((dj_profile.upi_id or "").strip())
    has_bank = bool((dj_profile.bank_account_number or "").strip() and (dj_profile.bank_ifsc_code or "").strip())
    if not (has_upi or has_bank):
        return Response(
            {"error": "Add a payout method first: UPI ID or bank account + IFSC (UPI/bank payouts only)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # One withdrawal a week, on any day the DJ likes (automatic weekly payouts count too).
    from datetime import timedelta

    from .models import Payout as _Payout

    last = _Payout.objects.filter(dj=dj_profile).exclude(status="failed").order_by("-created_at").first()
    if last and last.created_at > timezone.now() - timedelta(days=7):
        nxt = timezone.localtime(last.created_at + timedelta(days=7))
        return Response({"error": f"You can withdraw once a week. Your next withdrawal opens on {nxt:%d %b at %I:%M %p}."},
                        status=status.HTTP_400_BAD_REQUEST)
    # Verify OTP [Spec P2 §11]
    from apps.accounts.payout_auth import verify_payout_otp

    success, message = verify_payout_otp(dj_profile, code)
    if not success:
        return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

    if request.user.profile.is_frozen or request.user.profile.is_banned:
        return Response({"error": "Payouts are disabled on this account."}, status=status.HTTP_403_FORBIDDEN)
    if dj_profile.status != "approved":
        return Response({"error": "Your DJ profile is not approved."}, status=status.HTTP_403_FORBIDDEN)
    from .models import Payout

    if Payout.objects.filter(dj=dj_profile, status="held").exists():
        return Response({"error": "A payout hold is active on your account."}, status=status.HTTP_403_FORBIDDEN)

    # Process Payout (row-locked inside)
    from .payout_processor import _process_single_payout

    payout_amount = _process_single_payout(wallet.dj_id)

    if not payout_amount:
        return Response(
            {"error": "Insufficient funds or payout threshold not reached.", "threshold": "₹500"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    latest = Payout.objects.filter(dj=dj_profile).order_by("-created_at").first()
    st = latest.status if latest else "pending"
    if st == "completed":
        msg = f"Done. ₹{payout_amount} has been sent" + (f" (UTR {latest.utr})." if latest.utr else ".")
    elif st == "processing":
        msg = f"₹{payout_amount} is on its way to you. It usually arrives within minutes; we'll email you when it lands."
    elif st == "failed":
        msg = f"The transfer of ₹{payout_amount} didn't go through ({latest.failure_reason or 'declined'}). The money is back in your balance; check your payout details and try again."
    elif latest and (latest.hold_reason or "").startswith("Waiting for admin approval"):
        msg = f"Payout of ₹{payout_amount} requested. It needs a quick check by our team first, then it is sent automatically."
    else:
        msg = f"Payout of ₹{payout_amount} requested. You'll get it within 1–2 working days."
    return Response({"status": st if st in ("completed", "processing", "failed") else "initiated",
                     "message": msg, "payout_amount": str(payout_amount)})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def open_dispute(request):
    """Initiates a formal dispute for a purchase [Imp 01]."""
    purchase_id = request.data.get("purchase_id")
    reason = request.data.get("reason")

    if not purchase_id or not reason:
        return Response({"error": "purchase_id and reason are required."}, status=400)

    try:
        purchase = Purchase.objects.get(id=purchase_id, user=request.user.profile)
    except Purchase.DoesNotExist:
        return Response({"error": "Purchase not found."}, status=404)

    from .models import PurchaseDispute

    dispute = PurchaseDispute.objects.create(purchase=purchase, user=request.user.profile, reason=reason)

    return Response(
        {
            "status": "dispute_opened",
            "dispute_id": dispute.id,
            "message": "Dispute opened. Our support team will review it within 24-48 hours.",
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def my_library(request):
    """
    List all tracks/albums purchased by the user [Spec §3.1].
    Excludes revoked purchases.
    """
    purchases = Purchase.objects.filter(
        user=request.user.profile, status="paid", is_revoked=False  # Only show successful purchases [Spec §3.1]
    ).order_by("-created_at")

    serializer = PurchaseSerializer(purchases, many=True)
    return Response(serializer.data)


def pro_landing(request):
    """MixMint Pro landing page [Section B]. Public sales page (CTA gates on DJ)."""
    return render(request, "commerce/pro_landing.html")


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def activate_pro_trial(request):
    """Activates 7-day free trial for Pro Plan [Section B Step 5]"""
    profile = request.user.profile
    if profile.role != "dj":
        return Response({"error": "Only DJs can activate Pro Plan trials."}, status=status.HTTP_403_FORBIDDEN)

    if profile.is_pro_dj:
        return Response({"error": "You are already a Pro DJ."}, status=status.HTTP_400_BAD_REQUEST)
    dj_profile = getattr(profile, "dj_profile", None)
    if dj_profile is None or dj_profile.status != "approved":
        return Response({"error": "Your DJ profile must be approved first."}, status=status.HTTP_400_BAD_REQUEST)

    # One free trial per DJ, ever (checked again inside the lock so a double click can't start two).
    def used_trial(p):
        return p.pro_trial_ends_at is not None or ProSubscriptionEvent.objects.filter(dj=p.dj_profile, event_type="trial_start").exists()

    if used_trial(profile):
        return Response({"error": "You have already used your free trial."}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        profile = type(profile).objects.select_for_update().get(pk=profile.pk)
        if used_trial(profile) or profile.is_pro_dj:
            return Response({"error": "You have already used your free trial."}, status=status.HTTP_400_BAD_REQUEST)
        # Update Profile
        profile.is_pro_dj = True
        profile.pro_started_at = timezone.now()
        profile.pro_trial_ends_at = timezone.now() + timedelta(days=7)
        profile.pro_expires_at = profile.pro_trial_ends_at  # Trial ends = expires if not paid
        profile.storage_quota_mb = 20480  # 20 GB [Spec P3 §1.5]
        profile.save()

        # Log Event
        ProSubscriptionEvent.objects.create(
            dj=profile.dj_profile,
            event_type="trial_start",
            plan_type="monthly",  # Default
            amount_paise=0,
            gateway_order_id=f"TRIAL_{profile.user.id.hex[:8].upper()}",
        )

    return Response(
        {
            "status": "success",
            "message": "Pro Plan trial activated! You now have 7 days of Pro features.",
            "expires_at": profile.pro_expires_at.isoformat(),
        }
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def request_refund(request):
    """
    Buyer requests a refund [Section C Fix 01].
    Auto-refunded (and DJ credit reversed) only if the file was never delivered;
    otherwise queued for admin review.
    """
    purchase_id = request.data.get("purchase_id")
    reason = str(request.data.get("reason", ""))[:2000]

    if not purchase_id:
        return Response({"error": "Purchase ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        purchase = Purchase.objects.get(id=purchase_id, user=request.user.profile)
    except (Purchase.DoesNotExist, ValueError, TypeError):
        return Response({"error": "Purchase not found."}, status=status.HTTP_404_NOT_FOUND)

    if purchase.status != "paid" or purchase.is_revoked:
        return Response({"error": "Only paid purchases can be refunded."}, status=status.HTTP_400_BAD_REQUEST)

    if RefundRequest.objects.filter(purchase=purchase).exists():
        return Response(
            {"error": "Refund request already exists for this purchase."}, status=status.HTTP_400_BAD_REQUEST
        )

    from apps.downloads.models import DownloadLog

    delivered = (
        purchase.download_completed
        or DownloadLog.objects.filter(
            user=purchase.user,
            content_id=purchase.content_id,
            content_type=purchase.content_type,
            created_at__gte=purchase.created_at,
        ).exists()
    )
    eligible_for_auto = not delivered and bool(purchase.gateway_payment_id)

    refund_req = RefundRequest.objects.create(
        purchase=purchase,
        reason=reason,
        eligible_for_auto_refund=eligible_for_auto,
        is_automated=eligible_for_auto,
        status="pending",
    )
    if not eligible_for_auto:
        _alert_refund(refund_req)
        return Response(
            {"status": "pending", "message": "Refund request submitted for admin review.", "automated": False}
        )

    if not execute_refund(refund_req, note="Automatically approved: download not delivered."):
        refund_req.admin_notes = "Automatic refund failed at the gateway; needs manual processing."
        refund_req.save(update_fields=["admin_notes"])
        _alert_refund(refund_req)
        return Response(
            {"status": "pending", "message": "We couldn't refund automatically. Support will process it shortly."},
            status=status.HTTP_202_ACCEPTED,
        )
    return Response({"status": "success", "message": "Refund processed successfully.", "automated": True})


def execute_refund(refund_req, note=""):
    """Refund the buyer at the gateway and reverse the DJ's credit. Returns True on success."""
    from apps.payments.utils import get_gateway
    from .services import MonetizationService

    purchase = refund_req.purchase
    try:
        gateway = get_gateway(purchase.payment_gateway)
        amount = purchase.amount_paise if purchase.amount_paise is not None else int(purchase.price_paid * 100)
        refund_result = gateway.process_refund(
            purchase.gateway_payment_id if purchase.payment_gateway == "razorpay" else purchase.gateway_order_id,
            amount,
            reason=f"Refund: {refund_req.reason}"[:250],
        )
    except Exception:
        logger.exception("Refund failed for purchase %s", purchase.id)
        return False

    with transaction.atomic():
        MonetizationService.reverse_purchase(purchase, reason="refund")
        Purchase.objects.filter(pk=purchase.pk).update(
            status="refunded", gateway_refund_id=refund_result.get("refund_id"), refunded_at=timezone.now()
        )
        refund_req.status = "processed"
        refund_req.processed_at = timezone.now()
        refund_req.admin_notes = note or refund_req.admin_notes
        refund_req.save()
    return True


def _alert_refund(refund_req):
    try:
        from apps.admin_panel.telegram import notify_admins

        p = refund_req.purchase
        notify_admins(
            f"↩️ Refund request: ₹{p.price_paid} ({p.content_type} #{p.content_id}) from {p.user.user.email}\n"
            f"Reason: {refund_req.reason[:300]}\nReview it in Admin → Refunds."
        )
    except Exception:
        pass


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def toggle_wishlist(request):
    """Imp 13: Toggle a track in/out of the buyer's wishlist."""
    from .models import Wishlist
    from apps.tracks.models import Track

    track_id = request.data.get("track_id")
    if not track_id:
        return Response({"error": "track_id is required."}, status=400)

    try:
        track = Track.objects.get(id=track_id)
    except Track.DoesNotExist:
        return Response({"error": "Track not found."}, status=404)

    wishlist_item = Wishlist.objects.filter(user=request.user.profile, track=track)

    if wishlist_item.exists():
        wishlist_item.delete()
        return Response({"status": "removed", "is_wishlisted": False})
    else:
        # Prevent wishlisting owned tracks [Spec P3 §1.2]
        from .models import Purchase

        if Purchase.objects.filter(
            user=request.user.profile, content_id=track.id, content_type="track", status="paid"
        ).exists():
            return Response({"error": "You already own this track."}, status=400)

        Wishlist.objects.create(user=request.user.profile, track=track)
        return Response({"status": "added", "is_wishlisted": True})


class CartViewSet(viewsets.ModelViewSet):
    """API for managing shopping cart [Phase 3 Feature 3]."""

    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user.profile, is_active=True)

    @action(detail=False, methods=["GET"])
    def current(self, request):
        """Get or create the user's active cart."""
        cart, _ = Cart.objects.get_or_create(user=request.user.profile, is_active=True)
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=["POST"])
    def add_item(self, request):
        """Add an item to the active cart."""
        content_type = request.data.get("content_type")
        content_id = request.data.get("content_id")

        if not content_type or not content_id:
            return Response({"error": "content_type and content_id are required"}, status=400)

        try:
            if content_type == "track":
                from apps.tracks.models import Track

                content = Track.objects.get(id=content_id, is_active=True, is_deleted=False)
            elif content_type == "album":
                from apps.albums.models import AlbumPack

                content = AlbumPack.objects.get(id=content_id, is_active=True, is_deleted=False)
            else:
                return Response({"error": "Invalid content_type"}, status=400)
        except Exception:
            return Response({"error": "Item not found"}, status=404)

        # Prevent purchasing already-owned content
        if Purchase.objects.filter(
            user=request.user.profile, content_type=content_type, content_id=content_id, status="paid", is_revoked=False
        ).exists():
            return Response({"error": "You already own this item."}, status=400)

        # Prevent DJ from buying own content
        if hasattr(request.user.profile, "dj_profile") and request.user.profile.dj_profile == content.dj:
            return Response({"error": "You cannot purchase your own content."}, status=400)

        cart, _ = Cart.objects.get_or_create(user=request.user.profile, is_active=True)
        try:
            CartItem.objects.create(
                cart=cart, content_type=content_type, content_id=content_id, price=int(content.price * 100)
            )
        except Exception:
            return Response({"error": "Item is already in your cart."}, status=400)

        return Response(self.get_serializer(cart).data)

    @action(detail=False, methods=["POST"])
    def remove_item(self, request):
        """Remove an item from the active cart."""
        item_id = request.data.get("item_id")
        if not item_id:
            return Response({"error": "item_id is required"}, status=400)

        cart = Cart.objects.filter(user=request.user.profile, is_active=True).first()
        if not cart:
            return Response({"error": "No active cart found."}, status=404)

        deleted, _ = CartItem.objects.filter(id=item_id, cart=cart).delete()
        if not deleted:
            return Response({"error": "Item not found in cart."}, status=404)

        return Response(self.get_serializer(cart).data)

    @action(detail=False, methods=["POST"])
    def merge_guest_cart(self, request):
        """
        [P2-11.08 FIX] Merge guest cart into user cart on login.
        Called from frontend after login with guest_cart_items.
        """
        guest_items = request.data.get("guest_cart_items", [])
        if not guest_items:
            return Response({"message": "No items to merge"})

        cart, _ = Cart.objects.get_or_create(user=request.user.profile, is_active=True)
        merged_count = 0

        for item in guest_items:
            content_type = item.get("content_type")
            content_id = item.get("content_id")

            if not content_type or not content_id:
                continue

            # Skip if already owns the item
            if Purchase.objects.filter(
                user=request.user.profile,
                content_type=content_type,
                content_id=content_id,
                status="paid",
                is_revoked=False,
            ).exists():
                continue

            # Skip if already in cart
            if cart.items.filter(content_type=content_type, content_id=content_id).exists():
                continue

            # Validate content exists
            try:
                if content_type == "track":
                    from apps.tracks.models import Track

                    content = Track.objects.get(id=content_id, is_active=True, is_deleted=False)
                elif content_type == "album":
                    from apps.albums.models import AlbumPack

                    content = AlbumPack.objects.get(id=content_id, is_active=True, is_deleted=False)
                else:
                    continue
            except Exception:
                continue

            # Skip own content for DJs
            if hasattr(request.user.profile, "dj_profile") and request.user.profile.dj_profile == content.dj:
                continue

            try:
                CartItem.objects.create(
                    cart=cart, content_type=content_type, content_id=content_id, price=int(content.price * 100)
                )
                merged_count += 1
            except Exception:
                pass

        return Response(
            {"message": f"Merged {merged_count} items into your cart", "cart": self.get_serializer(cart).data}
        )

    @action(detail=False, methods=["POST"])
    def clear(self, request):
        """Clear all items from the active cart."""
        cart = Cart.objects.filter(user=request.user.profile, is_active=True).first()
        if cart:
            cart.items.all().delete()
            return Response(self.get_serializer(cart).data)
        return Response({"error": "No active cart found."}, status=404)
