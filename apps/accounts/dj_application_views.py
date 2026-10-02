"""
DJ Application views — handles the DJ onboarding flow [Spec §7, P2 §2].

Flow:
1. User submits DJ application
2. Admin approves/rejects
3. On approval: DJProfile + DJWallet created
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from apps.accounts.models import Profile, DJProfile
from apps.commerce.models import DJWallet, DJApplicationFee
from apps.admin_panel.email_utils import send_email


def submit_dj_application(user, data):
    """
    Submit a DJ application [Spec §7]. Returns (http_status, payload).
    Used by the API below and by the /apply-dj/ page.
    Checks:
    - User is not already a DJ
    - No pending application exists
    - Application fee paid (if enabled by admin)
    - FREE for first 3 months [Spec §7]
    """
    profile = user.profile

    # Already a DJ?
    if profile.role == "dj":
        return 400, {"error": "You are already a DJ."}

    # Already has a DJProfile?
    if hasattr(profile, "dj_profile"):
        return 400, {"error": "You already have a DJ profile."}

    # Check required fields
    dj_name = data.get("dj_name", "").strip()
    slug = data.get("slug", "").strip().lower()
    bio = data.get("bio", "").strip()
    genres = data.get("genres", [])
    if isinstance(genres, str):  # the web form sends "Techno, House"
        import re as _re

        genres = [g.strip() for g in _re.split(r"[,/|]+", genres) if g.strip()]
    legal_agreement = data.get("legal_agreement_accepted", False) in (True, "true", "on", "1", 1, "True")

    if not dj_name:
        return 400, {"error": "DJ name is required."}
    if not slug:
        return 400, {"error": "URL slug is required."}
    if not legal_agreement:
        return 400, {"error": "You must accept the legal agreement to proceed."}

    from django.utils.text import slugify

    if slugify(slug) != slug or len(slug) < 3 or len(slug) > 50:
        return 400, {"error": "URL slug must be 3-50 lowercase letters, numbers or hyphens."}
    if len(dj_name) > 100 or len(bio) > 2000:
        return 400, {"error": "DJ name or bio is too long."}
    RESERVED = {"admin", "api", "static", "media", "dashboard", "login", "signup", "logout", "explore", "djs"}
    if slug in RESERVED:
        return 400, {"error": "This URL slug is reserved."}

    # Check slug uniqueness
    if DJProfile.objects.filter(slug=slug).exists():
        return 400, {"error": "This URL slug is already taken."}

    # Check application fee requirement [Spec §7: ₹99 intro, free first 3 months]
    from apps.admin_panel.models import PlatformSettings

    settings_obj = PlatformSettings.load()
    fee_enabled = settings_obj.dj_application_fee_enabled
    fee_amount = settings_obj.dj_application_fee

    # Where to listen to them + where they're based (reviewers need at least one link)
    from urllib.parse import urlsplit

    raw_links = data.getlist("links") if hasattr(data, "getlist") else data.get("links", [])
    if isinstance(raw_links, str):
        raw_links = [raw_links]
    links = []
    for link in raw_links or []:
        link = str(link or "").strip()
        if not link:
            continue
        if not link.startswith(("http://", "https://")):
            link = "https://" + link
        host = (urlsplit(link).hostname or "").lower()
        if "." not in host:
            return 400, {"error": f"“{link}” doesn't look like a link."}
        if host.endswith(("drive.google.com", "docs.google.com")):
            return 400, {"error": "Please share a YouTube, Instagram, SoundCloud or Mixcloud link — not Google Drive."}
        links.append(link[:300])
    if not links:
        return 400, {"error": "Add at least one link to your music (YouTube, Instagram, SoundCloud…)."}
    links = links[:3]
    instagram = str(data.get("instagram") or "").strip().lstrip("@")[:60]
    city = str(data.get("city") or "").strip()[:120]

    # Create DJProfile in pending status
    dj_profile = DJProfile.objects.create(
        profile=profile,
        dj_name=dj_name,
        slug=slug,
        bio=bio,
        genres=[str(g)[:40] for g in genres][:10] if isinstance(genres, list) else [],
        location=city or None,
        application_links=links,
        social_links={"instagram": f"https://instagram.com/{instagram}"} if instagram else {},
        status="pending_payment" if fee_enabled else "pending_review",
    )

    try:
        from apps.admin_panel.telegram import notify_admins

        notify_admins(
            f"🎛 New DJ application: {dj_name} ({user.email}){' · ' + city if city else ''}\n"
            + "\n".join(links)
            + "\nReview it in Admin → DJs."
        )
    except Exception:
        pass

    # Create application fee record if fee is enabled
    if fee_enabled:
        DJApplicationFee.objects.create(
            dj=dj_profile,
            amount=fee_amount,
            status="pending",
        )
        return 201, {
                "status": "pending_payment",
                "message": f"Application submitted. Please pay ₹{fee_amount} application fee.",
                "fee_required": True,
                "fee_amount": fee_amount,
                "dj_profile_id": dj_profile.id,
            }
    else:
        return 201, {
                "status": "pending_review",
                "message": "Application submitted. Waiting for admin approval.",
                "fee_required": False,
                "dj_profile_id": dj_profile.id,
            }


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def apply_as_dj(request):
    code, payload = submit_dj_application(request.user, request.data)
    return Response(payload, status=code)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def admin_approve_dj(request, dj_profile_id):
    """
    Admin approves a DJ application [Spec §3.3].
    Creates DJWallet and updates user role.
    """
    try:
        dj_profile = DJProfile.objects.get(id=dj_profile_id)
    except DJProfile.DoesNotExist:
        return Response({"error": "DJ profile not found."}, status=status.HTTP_404_NOT_FOUND)

    if dj_profile.status == "approved":
        return Response({"error": "Already approved."}, status=status.HTTP_400_BAD_REQUEST)

    # Check fee paid (if required)
    try:
        fee = dj_profile.application_fee
        if fee.status not in ("paid", "waived"):
            return Response({"error": "Application fee not paid yet."}, status=status.HTTP_400_BAD_REQUEST)
    except DJApplicationFee.DoesNotExist:
        pass  # Fee not required / waived

    # Approve
    dj_profile.status = "approved"
    dj_profile.save(update_fields=["status"])

    # Update user role
    profile = dj_profile.profile
    profile.role = "dj"
    profile.save(update_fields=["role"])

    # Create DJ Wallet [Spec P2 §9]
    DJWallet.objects.get_or_create(dj=dj_profile)

    # Signed up through another DJ's link? Record the referral (max 50 per DJ).
    from apps.commerce.referrals import link_on_approval

    link_on_approval(dj_profile)

    # Send welcome email via Resend [Spec: Welcome email on DJ approval]
    try:
        from django.utils.html import escape

        send_email(
            to_email=profile.user.email,
            subject="Welcome to MixMint DJ!",
            html_content=(
                f"<p>Hi {escape(dj_profile.dj_name)},</p>"
                f"<p>Your DJ application has been <strong>approved</strong>. "
                f"Your storefront is now live on MixMint.</p>"
                f"<p>Log in to upload tracks and album packs to get started.</p>"
            ),
        )
    except Exception:
        # Email failures must not break admin actions
        pass

    return Response(
        {
            "status": "approved",
            "message": f"{dj_profile.dj_name} has been approved as a DJ.",
            "dj_profile_id": dj_profile.id,
        }
    )


@api_view(["POST"])
@permission_classes([IsAdminUser])
def admin_reject_dj(request, dj_profile_id):
    """Admin rejects a DJ application [Spec §3.3]."""
    try:
        dj_profile = DJProfile.objects.get(id=dj_profile_id)
    except DJProfile.DoesNotExist:
        return Response({"error": "DJ profile not found."}, status=status.HTTP_404_NOT_FOUND)

    from django.utils.html import escape

    reason = str(request.data.get("reason") or "Application rejected by admin.")[:1000]

    dj_profile.status = "rejected"
    dj_profile.save(update_fields=["status"])

    # Notify applicant via Resend [Spec: Rejection email]
    try:
        send_email(
            to_email=dj_profile.profile.user.email,
            subject="MixMint DJ Application Update",
            html_content=(
                f"<p>Hi {escape(dj_profile.dj_name)},</p>"
                f"<p>Your DJ application was <strong>rejected</strong>.</p>"
                f"<p>Reason: {escape(reason)}</p>"
                f"<p>If you believe this is an error, reply to this email for a manual review.</p>"
            ),
        )
    except Exception:
        pass

    return Response(
        {
            "status": "rejected",
            "message": f"{dj_profile.dj_name} application has been rejected.",
            "reason": reason,
        }
    )


@api_view(["POST"])
@permission_classes([IsAdminUser])
def admin_verify_dj(request, dj_profile_id):
    """Grant Verified DJ badge [Spec P2 §2]."""
    try:
        dj_profile = DJProfile.objects.get(id=dj_profile_id, status="approved")
    except DJProfile.DoesNotExist:
        return Response({"error": "Approved DJ profile not found."}, status=status.HTTP_404_NOT_FOUND)

    dj_profile.profile.is_verified_dj = True
    dj_profile.profile.save(update_fields=["is_verified_dj"])

    return Response(
        {
            "status": "verified",
            "message": f"{dj_profile.dj_name} is now a Verified DJ.",
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_store_pause(request):
    """DJ pauses/unpauses their store [Spec §3.2]."""
    if request.user.profile.role != "dj" or not hasattr(request.user.profile, "dj_profile"):
        return Response({"error": "Only DJs can access this."}, status=status.HTTP_403_FORBIDDEN)

    try:
        dj_profile = request.user.profile.dj_profile
    except (Profile.DoesNotExist, DJProfile.DoesNotExist):
        return Response({"error": "DJ profile not found."}, status=status.HTTP_404_NOT_FOUND)

    profile = dj_profile.profile
    profile.store_paused = not profile.store_paused
    profile.save(update_fields=["store_paused"])

    return Response(
        {
            "store_paused": profile.store_paused,
            "message": "Store paused." if profile.store_paused else "Store resumed.",
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def request_payout_otp(request):
    """
    DJ requests a 2FA OTP for payout verification [Spec P2 §11, P3 §3.2].
    OTP is sent to the DJ's registered email.
    """
    if request.user.profile.role != "dj" or not hasattr(request.user.profile, "dj_profile"):
        return Response({"error": "Only DJs can request payout OTPs."}, status=status.HTTP_403_FORBIDDEN)

    try:
        dj_profile = request.user.profile.dj_profile
    except (Profile.DoesNotExist, DJProfile.DoesNotExist):
        return Response({"error": "DJ profile not found."}, status=status.HTTP_404_NOT_FOUND)

    # Payouts are protected by TOTP (Google Authenticator / Authy), not emailed codes.
    if not dj_profile.payout_otp_secret:
        return Response(
            {
                "error": "Set up two-factor authentication first.",
                "setup_url": "/dashboard/dj/2fa/enable/",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response({"message": "Open your authenticator app and enter the current 6-digit code."})
