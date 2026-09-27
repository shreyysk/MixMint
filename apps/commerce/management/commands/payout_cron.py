import logging
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum

from apps.accounts.models import Profile, DJProfile
from apps.tracks.models import Track
from apps.albums.models import AlbumPack
from apps.commerce.models import StorageOverage, ProSubscriptionEvent
from apps.core.email_service import EmailService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Processes Pro Plan renewals and storage overage billing [Phase 1 Section B]"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting MixMint Payout & Billing Cron..."))

        # 1. Process Pro Renewals (Check for expired plans)
        self.process_pro_renewals()

        # 2. Process Storage Overage (Monthly billing)
        self.process_storage_overage()

    def process_pro_renewals(self):
        # Find DJs whose Pro plan has expired
        expired_profiles = Profile.objects.filter(
            is_pro_dj=True, pro_expires_at__lt=timezone.now(), pro_grace_ends_at__isnull=True  # Not already in grace
        )

        for profile in expired_profiles:
            # Grant 7-day grace period [Spec P3 §1.5]
            profile.pro_grace_ends_at = profile.pro_expires_at + datetime.timedelta(days=7)
            profile.save()
            logger.info(f"DJ {profile.user.email} entered Pro Plan grace period until {profile.pro_grace_ends_at}")
            EmailService.send_notice(
                profile.user.email,
                "Your MixMint Pro plan has expired - 7 days to renew",
                "Your Pro plan has expired",
                [
                    "Your MixMint Pro plan ran out, so you are now in a 7-day grace period.",
                    f"Renew before {profile.pro_grace_ends_at:%d %b %Y} to keep Pro commission rates and storage.",
                    "After that your account moves back to the free plan (3 GB storage).",
                ],
                cta_label="Renew Pro",
                cta_path="/dashboard/dj/",
            )

        # Check for grace period lapses
        lapsed_profiles = Profile.objects.filter(is_pro_dj=True, pro_grace_ends_at__lt=timezone.now())

        for profile in lapsed_profiles:
            with transaction.atomic():
                profile.is_pro_dj = False
                profile.pro_grace_ends_at = None
                profile.storage_quota_mb = 3072  # Back to 3GB
                profile.save()

                ProSubscriptionEvent.objects.create(
                    dj=profile.dj_profile,
                    event_type="subscription_lapsed",
                    plan_type=profile.pro_plan_type or "monthly",
                    amount_paise=0,
                    gateway_order_id=f"LAPSE_{profile.user.id.hex[:8].upper()}",
                )
                logger.warning(f"DJ {profile.user.email} Pro Plan LAPSED and downgraded.")
            EmailService.send_notice(
                profile.user.email,
                "Your MixMint Pro plan has ended",
                "You're back on the free plan",
                [
                    "Your Pro grace period ended, so your account is now on the free plan.",
                    "Your tracks stay online. Upgrade again any time to get Pro rates and storage back.",
                ],
                cta_label="Upgrade to Pro",
                cta_path="/dashboard/dj/",
            )

    def process_storage_overage(self):
        """
        Calculates overage for the previous month.
        Bills ₹30/GB/month [Spec P3 §1.5].
        """
        # Run on the 1st of every month
        if timezone.now().day != 1:
            return

        last_month = timezone.now() - datetime.timedelta(days=1)
        billing_month_start = last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        djs = DJProfile.objects.filter(profile__is_pro_dj=True, overage_enabled=True)

        for dj in djs:
            total_bytes = 0
            track_storage = (
                Track.objects.filter(dj=dj, is_deleted=False).aggregate(total=Sum("file_size"))["total"] or 0
            )
            album_storage = (
                AlbumPack.objects.filter(dj=dj, is_deleted=False).aggregate(total=Sum("file_size"))["total"] or 0
            )
            total_bytes = track_storage + album_storage

            usage_mb = total_bytes / (1024 * 1024)
            quota_mb = dj.profile.storage_quota_mb

            if usage_mb > quota_mb:
                overage_mb = usage_mb - quota_mb
                overage_gb = overage_mb / 1024.0
                # ₹30 per GB, min 0.1 GB
                billing_gb = max(overage_gb, 0.1)
                amount_paise = int(billing_gb * 30 * 100)

                # Check if already billed for this month
                if not StorageOverage.objects.filter(dj=dj, billing_month=billing_month_start).exists():
                    StorageOverage.objects.create(
                        dj=dj,
                        billing_month=billing_month_start,
                        usage_bytes=total_bytes,
                        overage_bytes=int(overage_mb * 1024 * 1024),
                        amount_paise=amount_paise,
                        status="pending",
                    )
                    logger.info(f"Generated overage bill for {dj.dj_name}: ₹{amount_paise / 100.0}")
                    # No card-on-file billing: the DJ pays the pending bill from the dashboard.
                    EmailService.send_notice(
                        dj.profile.user.email,
                        "MixMint storage overage bill",
                        "You went over your storage quota",
                        [
                            f"Last month you used {usage_mb / 1024:.2f} GB against a {quota_mb / 1024:.2f} GB quota.",
                            f"Overage charge: ₹{amount_paise / 100:.2f} (₹30 per extra GB).",
                            "Pay it from your dashboard, or delete files to avoid next month's charge.",
                        ],
                        cta_label="Open dashboard",
                        cta_path="/dashboard/dj/",
                    )
