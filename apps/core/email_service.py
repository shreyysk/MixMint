"""
MixMint Email Notification Service.

Handles all transactional emails using Django templates.
"""

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
            html_content = render_to_string(f'emails/{template_name}.html', context)
            
            send_mail(
                subject=subject,
                message='',  # Plain text fallback
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
    
    # ============================================
    # DJ EMAILS
    # ============================================
    
    @classmethod
    def send_dj_welcome(cls, dj_profile):
        """Send welcome email to newly approved DJ."""
        from apps.accounts.models import AmbassadorCode
        
        code, _ = AmbassadorCode.objects.get_or_create(
            dj=dj_profile,
            defaults={'code': f"DJ{dj_profile.id.hex[:8].upper()}"}
        )
        
        return cls.send_email(
            to_email=dj_profile.profile.user.email,
            subject="Welcome to MixMint! 🎧 Your DJ account is approved",
            template_name='dj_welcome',
            context={
                'dj_name': dj_profile.dj_name,
                'referral_code': code.code,
            }
        )
    
    @classmethod
    def send_sale_notification(cls, dj_profile, purchase, track):
        """Notify DJ of a new sale."""
        from apps.commerce.models import Purchase, DJWallet
        from apps.commerce.dj_conversion import DJMilestoneReward
        
        wallet = DJWallet.objects.filter(dj=dj_profile).first()
        total_sales = Purchase.objects.filter(seller=dj_profile, status='paid').count()
        
        # Check if first sale
        is_first_sale = total_sales == 1
        
        # Check for new milestones
        new_milestones = DJMilestoneReward.check_and_award(dj_profile)
        milestone_achieved = None
        milestone_reward = 0
        if new_milestones:
            milestone = DJMilestoneReward.objects.filter(
                dj=dj_profile, milestone=new_milestones[0]
            ).first()
            if milestone:
                milestone_achieved = milestone.get_milestone_display()
                milestone_reward = milestone.reward_amount
        
        return cls.send_email(
            to_email=dj_profile.profile.user.email,
            subject=f"💰 You made a sale! {track.title}",
            template_name='sale_notification',
            context={
                'dj_name': dj_profile.dj_name,
                'track_title': track.title,
                'earnings': str(purchase.dj_earnings),
                'total_sales': total_sales,
                'total_earnings': str(wallet.total_earnings if wallet else 0),
                'is_first_sale': is_first_sale,
                'milestone_achieved': milestone_achieved,
                'milestone_name': milestone_achieved,
                'milestone_reward': str(milestone_reward),
            }
        )
    
    @classmethod
    def send_payout_initiated(cls, dj_profile, payout):
        """Notify DJ of payout initiation."""
        from apps.accounts.models import BankAccount
        
        bank = BankAccount.objects.filter(dj=dj_profile, is_primary=True).first()
        bank_last_4 = bank.account_number[-4:] if bank else '****'
        
        return cls.send_email(
            to_email=dj_profile.profile.user.email,
            subject=f"💸 Payout of ₹{payout.amount} initiated",
            template_name='payout_initiated',
            context={
                'dj_name': dj_profile.dj_name,
                'payout_amount': str(payout.amount),
                'payout_id': payout.id,
                'bank_last_4': bank_last_4,
                'expected_date': (payout.created_at.date() + timedelta(days=3)).strftime('%b %d, %Y'),
            }
        )
    
    @classmethod
    def send_referral_success(cls, referrer_dj, referred_dj):
        """Notify DJ when their referral makes first sale."""
        from apps.commerce.dj_conversion import DJReferralProgram
        from apps.accounts.models import AmbassadorCode
        
        referrals = DJReferralProgram.objects.filter(referrer=referrer_dj)
        code = AmbassadorCode.objects.filter(dj=referrer_dj).first()
        
        referral_url = f"https://mixmint.in/join?ref={code.code}" if code else ""
        share_msg = f"Join MixMint! Use code {code.code}"
        
        return cls.send_email(
            to_email=referrer_dj.profile.user.email,
            subject=f"🎉 Your referral {referred_dj.dj_name} made a sale! +₹100",
            template_name='referral_success',
            context={
                'dj_name': referrer_dj.dj_name,
                'referred_dj_name': referred_dj.dj_name,
                'total_referrals': referrals.count(),
                'total_referral_earnings': referrals.filter(referrer_paid=True).count() * 100,
                'referral_code': code.code if code else '',
                'whatsapp_url': f"https://wa.me/?text={share_msg}%20{referral_url}",
                'twitter_url': f"https://twitter.com/intent/tweet?text={share_msg}&url={referral_url}",
                'telegram_url': f"https://t.me/share/url?url={referral_url}&text={share_msg}",
            }
        )
    
    @classmethod
    def send_milestone_achieved(cls, dj_profile, milestone):
        """Notify DJ of milestone achievement."""
        from apps.commerce.models import Purchase, DJWallet
        from apps.commerce.dj_conversion import DJMilestoneReward
        
        wallet = DJWallet.objects.filter(dj=dj_profile).first()
        total_sales = Purchase.objects.filter(seller=dj_profile, status='paid').count()
        
        # Find next milestone
        all_milestones = list(DJMilestoneReward.MILESTONES)
        achieved = list(DJMilestoneReward.objects.filter(dj=dj_profile).values_list('milestone', flat=True))
        next_milestone = None
        
        for m_key, m_name in all_milestones:
            if m_key not in achieved:
                next_milestone = {
                    'name': m_name,
                    'reward': DJMilestoneReward.REWARDS[m_key],
                }
                break
        
        return cls.send_email(
            to_email=dj_profile.profile.user.email,
            subject=f"🏆 Milestone Unlocked: {milestone.get_milestone_display()}!",
            template_name='milestone_achieved',
            context={
                'dj_name': dj_profile.dj_name,
                'milestone_name': milestone.get_milestone_display(),
                'reward_amount': str(milestone.reward_amount),
                'total_sales': total_sales,
                'total_earnings': str(wallet.total_earnings if wallet else 0),
                'next_milestone': next_milestone,
                'next_milestone_name': next_milestone['name'] if next_milestone else None,
                'next_milestone_reward': str(next_milestone['reward']) if next_milestone else None,
            }
        )
    
    # ============================================
    # BUYER EMAILS
    # ============================================
    
    @classmethod
    def send_purchase_confirmation(cls, purchase):
        """Send purchase confirmation to buyer."""
        from apps.tracks.models import Track
        from apps.albums.models import AlbumPack
        
        if purchase.content_type == 'track':
            content = Track.objects.filter(id=purchase.content_id).first()
        else:
            content = AlbumPack.objects.filter(id=purchase.content_id).first()
        
        if not content:
            return False
        
        return cls.send_email(
            to_email=purchase.user.user.email,
            subject=f"🎵 Your purchase: {content.title}",
            template_name='purchase_confirmation',
            context={
                'buyer_name': purchase.user.full_name or purchase.user.user.email,
                'content_title': content.title,
                'dj_name': content.dj.dj_name,
                'amount_paid': str(purchase.price_paid),
                'order_id': str(purchase.id)[:8],
                'purchase_date': purchase.created_at.strftime('%b %d, %Y %H:%M'),
                'download_url': f"https://mixmint.in/library",
            }
        )


# Import timedelta for payout email
from datetime import timedelta
