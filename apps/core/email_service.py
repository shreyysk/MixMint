"""
MixMint Email Notification Service.

Handles all transactional emails using Django templates.
"""

from datetime import timedelta
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Centralized email service for MixMint."""

    FROM_EMAIL = settings.DEFAULT_FROM_EMAIL

    @classmethod
    def send_email(cls, to_email, subject, template_name, context):
        """Send templated email."""
        try:
            context = {"site_url": getattr(settings, "BASE_URL", "https://mixmint.site").rstrip("/"), **(context or {})}
            html_content = render_to_string(f"emails/{template_name}.html", context)

            send_mail(
                subject=subject,
                message="",  # Plain text fallback
                from_email=cls.FROM_EMAIL,
                recipient_list=[to_email],
                html_message=html_content,
                fail_silently=False,
            )
            logger.info(f"Email sent: {template_name} to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Email failed: {template_name} to {to_email} - {str(e)}")
            return False

    @classmethod
    def send_notice(cls, to_email, subject, heading, lines, cta_label=None, cta_path=None):
        """Plain transactional notice (one heading, a few paragraphs, optional button)."""
        return cls.send_email(
            to_email=to_email,
            subject=subject,
            template_name="notice",
            context={"heading": heading, "lines": list(lines), "cta_label": cta_label, "cta_path": cta_path},
        )

    # ============================================
    # DJ EMAILS
    # ============================================

    @classmethod
    def send_dj_welcome(cls, dj_profile):
        """Send welcome email to newly approved DJ."""
        from apps.accounts.models import AmbassadorCode

        code, _ = AmbassadorCode.objects.get_or_create(
            dj=dj_profile, defaults={"code": f"DJ{dj_profile.id.hex[:8].upper()}"}
        )

        return cls.send_email(
            to_email=dj_profile.profile.user.email,
            subject="Welcome to MixMint! 🎧 Your DJ account is approved",
            template_name="dj_welcome",
            context={
                "dj_name": dj_profile.dj_name,
                "referral_code": code.code,
            },
        )

    @classmethod
    def send_sale_notification(cls, dj_profile, purchase, track):
        """Notify DJ of a new sale."""
        from apps.commerce.models import Purchase, DJWallet
        from apps.commerce.dj_conversion import DJMilestoneReward

        wallet = DJWallet.objects.filter(dj=dj_profile).first()
        total_sales = Purchase.objects.filter(seller=dj_profile, status="paid").count()

        # Check if first sale
        is_first_sale = total_sales == 1

        # Check for new milestones
        new_milestones = DJMilestoneReward.check_and_award(dj_profile)
        milestone_achieved = None
        milestone_reward = 0
        if new_milestones:
            milestone = DJMilestoneReward.objects.filter(dj=dj_profile, milestone=new_milestones[0]).first()
            if milestone:
                milestone_achieved = milestone.get_milestone_display()
                milestone_reward = milestone.reward_amount

        return cls.send_email(
            to_email=dj_profile.profile.user.email,
            subject=f"💰 You made a sale! {track.title}",
            template_name="sale_notification",
            context={
                "dj_name": dj_profile.dj_name,
                "track_title": track.title,
                "earnings": str(purchase.dj_earnings),
                "total_sales": total_sales,
                "total_earnings": str(wallet.total_earnings if wallet else 0),
                "is_first_sale": is_first_sale,
                "milestone_achieved": milestone_achieved,
                "milestone_name": milestone_achieved,
                "milestone_reward": str(milestone_reward),
            },
        )

    @classmethod
    def send_payout_initiated(cls, dj_profile, payout):
        """Notify DJ of payout initiation."""
        account = (dj_profile.bank_account_number or "").strip()
        bank_last_4 = account[-4:] if account else "****"

        return cls.send_email(
            to_email=dj_profile.profile.user.email,
            subject=f"Payout of ₹{payout.amount} on its way",
            template_name="payout_initiated",
            context={
                "dj_name": dj_profile.dj_name,
                "payout_amount": str(payout.amount),
                "payout_id": payout.id,
                "bank_last_4": bank_last_4,
                "expected_date": (payout.created_at.date() + timedelta(days=3)).strftime("%b %d, %Y"),
            },
        )

    @classmethod
    def send_referral_success(cls, referrer_dj, referred_dj):
        """Notify DJ when their referral makes first sale."""
        from apps.commerce.dj_conversion import DJReferralProgram
        from apps.accounts.models import AmbassadorCode

        referrals = DJReferralProgram.objects.filter(referrer=referrer_dj)
        code = AmbassadorCode.objects.filter(dj=referrer_dj).first()

        base = getattr(settings, "BASE_URL", "https://mixmint.site").rstrip("/")
        referral_url = f"{base}/?ref={code.code}" if code else ""
        share_msg = f"Join MixMint! Use code {code.code}"

        return cls.send_email(
            to_email=referrer_dj.profile.user.email,
            subject=f"🎉 Your referral {referred_dj.dj_name} made a sale! +₹100",
            template_name="referral_success",
            context={
                "dj_name": referrer_dj.dj_name,
                "referred_dj_name": referred_dj.dj_name,
                "total_referrals": referrals.count(),
                "total_referral_earnings": referrals.filter(referrer_paid=True).count() * 100,
                "referral_code": code.code if code else "",
                "whatsapp_url": f"https://wa.me/?text={share_msg}%20{referral_url}",
                "twitter_url": f"https://twitter.com/intent/tweet?text={share_msg}&url={referral_url}",
                "telegram_url": f"https://t.me/share/url?url={referral_url}&text={share_msg}",
            },
        )

    @classmethod
    def send_milestone_achieved(cls, dj_profile, milestone):
        """Notify DJ of milestone achievement."""
        from apps.commerce.models import Purchase, DJWallet
        from apps.commerce.dj_conversion import DJMilestoneReward

        wallet = DJWallet.objects.filter(dj=dj_profile).first()
        total_sales = Purchase.objects.filter(seller=dj_profile, status="paid").count()

        # Find next milestone
        all_milestones = list(DJMilestoneReward.MILESTONES)
        achieved = list(DJMilestoneReward.objects.filter(dj=dj_profile).values_list("milestone", flat=True))
        next_milestone = None

        for m_key, m_name in all_milestones:
            if m_key not in achieved:
                next_milestone = {
                    "name": m_name,
                    "reward": DJMilestoneReward.REWARDS[m_key],
                }
                break

        return cls.send_email(
            to_email=dj_profile.profile.user.email,
            subject=f"🏆 Milestone Unlocked: {milestone.get_milestone_display()}!",
            template_name="milestone_achieved",
            context={
                "dj_name": dj_profile.dj_name,
                "milestone_name": milestone.get_milestone_display(),
                "reward_amount": str(milestone.reward_amount),
                "total_sales": total_sales,
                "total_earnings": str(wallet.total_earnings if wallet else 0),
                "next_milestone": next_milestone,
                "next_milestone_name": next_milestone["name"] if next_milestone else None,
                "next_milestone_reward": str(next_milestone["reward"]) if next_milestone else None,
            },
        )

    # ============================================
    # BUYER EMAILS
    # ============================================

    @classmethod
    def library_link(cls, user):
        """Library link for the receipt. Guest buyers (no password yet) get a one-time sign-in link instead,
        so checkout doesn't need a separate "your account" email."""
        base = getattr(settings, "BASE_URL", "https://mixmint.site").rstrip("/")
        try:
            if not user.has_usable_password():
                from django.core import signing

                from apps.core.catalog_views import LINK_SALT

                token = signing.dumps({"u": str(user.pk), "l": user.last_login.isoformat() if user.last_login else ""}, salt=LINK_SALT)
                return f"{base}/recover/{token}/"
        except Exception:
            pass
        return f"{base}/library/"

    @classmethod
    def send_order_receipt(cls, purchases):
        """One receipt per checkout, however many items were in the cart."""
        purchases = [p for p in purchases if p is not None]
        if not purchases:
            return False
        if len(purchases) == 1:
            return cls.send_purchase_confirmation(purchases[0])
        from apps.albums.models import AlbumPack
        from apps.tracks.models import Track

        lines, total = [], 0
        for p in purchases:
            model = Track if p.content_type == "track" else AlbumPack
            item = model.objects.filter(id=p.content_id).select_related("dj").first()
            lines.append(f"{item.title if item else p.content_type} by {item.dj.dj_name if item else 'MixMint'}: ₹{p.price_paid}")
            total += p.price_paid or 0
        user = purchases[0].user.user
        link = cls.library_link(user)
        return cls.send_notice(
            user.email, f"Your purchase: {len(purchases)} items (₹{total})", "Thanks for your order",
            lines + [f"Total paid: ₹{total}. Everything is ready in your library."],
            cta_label="Download now", cta_path=link.replace(getattr(settings, "BASE_URL", "https://mixmint.site").rstrip("/"), "") or "/library/",
        )

    @classmethod
    def send_purchase_confirmation(cls, purchase):
        """Send purchase confirmation to buyer."""
        from apps.tracks.models import Track
        from apps.albums.models import AlbumPack

        if purchase.content_type == "track":
            content = Track.objects.filter(id=purchase.content_id).first()
        else:
            content = AlbumPack.objects.filter(id=purchase.content_id).first()

        if not content:
            return False

        return cls.send_email(
            to_email=purchase.user.user.email,
            subject=f"🎵 Your purchase: {content.title}",
            template_name="purchase_confirmation",
            context={
                "buyer_name": purchase.user.full_name or purchase.user.user.email,
                "content_title": content.title,
                "dj_name": content.dj.dj_name,
                "amount_paid": str(purchase.price_paid),
                "order_id": str(purchase.id)[:8],
                "purchase_date": purchase.created_at.strftime("%b %d, %Y %H:%M"),
                "download_url": cls.library_link(purchase.user.user),
                "payment_method": {"razorpay": "Razorpay", "phonepe": "PhonePe"}.get(purchase.payment_gateway or "", "Online payment"),
                "insurance_price": "49",
            },
        )


# Import timedelta for payout email
