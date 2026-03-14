"""
MixMint DJ Conversion & Retention System [High Conversion Enhancement].

Features for increasing DJ signups and retention:
1. Welcome bonus for new DJs
2. Referral bonus system (DJ refers DJ)
3. First sale celebration & milestone rewards
4. Reduced commission promotional periods
5. Quick onboarding with progress tracking
"""

from decimal import Decimal
from django.db import models, transaction
from django.utils import timezone
from django.conf import settings
import secrets


class DJWelcomeBonus(models.Model):
    """Welcome bonus credited to new DJs after first track upload."""
    dj = models.OneToOneField('accounts.DJProfile', on_delete=models.CASCADE, related_name='welcome_bonus')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('50.00'))
    credited = models.BooleanField(default=False)
    credited_at = models.DateTimeField(null=True, blank=True)
    
    @classmethod
    def credit_welcome_bonus(cls, dj_profile):
        """Credit ₹50 welcome bonus after first track upload."""
        bonus, created = cls.objects.get_or_create(dj=dj_profile)
        if bonus.credited:
            return False, "Welcome bonus already credited"
        
        with transaction.atomic():
            from apps.commerce.models import DJWallet, LedgerEntry
            wallet, _ = DJWallet.objects.get_or_create(dj=dj_profile)
            
            from django.db.models import F
            wallet.total_earnings = F('total_earnings') + bonus.amount
            wallet.pending_earnings = F('pending_earnings') + bonus.amount
            wallet.save(update_fields=['total_earnings', 'pending_earnings'])
            
            LedgerEntry.objects.create(
                wallet=wallet,
                amount=bonus.amount,
                entry_type='credit',
                description='Welcome bonus - First track uploaded! 🎉',
                metadata={'type': 'welcome_bonus'}
            )
            
            bonus.credited = True
            bonus.credited_at = timezone.now()
            bonus.save()
            
        return True, f"₹{bonus.amount} welcome bonus credited!"


class DJReferralProgram(models.Model):
    """DJ-to-DJ referral system for high conversion."""
    referrer = models.ForeignKey('accounts.DJProfile', on_delete=models.CASCADE, related_name='referrals_made')
    referred = models.ForeignKey('accounts.DJProfile', on_delete=models.CASCADE, related_name='referred_by')
    referral_code = models.CharField(max_length=20)
    
    # Bonus amounts
    referrer_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('100.00'))
    referred_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('50.00'))
    
    # Status tracking
    referrer_paid = models.BooleanField(default=False)
    referred_paid = models.BooleanField(default=False)
    
    # Triggered after referred DJ makes first sale
    first_sale_achieved = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('referrer', 'referred')
    
    @classmethod
    def process_first_sale_bonus(cls, dj_profile):
        """Credit referral bonuses when referred DJ makes first sale."""
        try:
            referral = cls.objects.get(referred=dj_profile, first_sale_achieved=False)
        except cls.DoesNotExist:
            return
        
        with transaction.atomic():
            from apps.commerce.models import DJWallet, LedgerEntry
            from django.db.models import F
            
            # Credit referrer bonus (₹100)
            if not referral.referrer_paid:
                referrer_wallet, _ = DJWallet.objects.get_or_create(dj=referral.referrer)
                referrer_wallet.total_earnings = F('total_earnings') + referral.referrer_bonus
                referrer_wallet.pending_earnings = F('pending_earnings') + referral.referrer_bonus
                referrer_wallet.save(update_fields=['total_earnings', 'pending_earnings'])
                
                LedgerEntry.objects.create(
                    wallet=referrer_wallet,
                    amount=referral.referrer_bonus,
                    entry_type='credit',
                    description=f'Referral bonus - {dj_profile.dj_name} made first sale! 🎊',
                    metadata={'type': 'referral_bonus', 'referred_dj': str(dj_profile.id)}
                )
                referral.referrer_paid = True
            
            # Credit referred DJ bonus (₹50)
            if not referral.referred_paid:
                referred_wallet, _ = DJWallet.objects.get_or_create(dj=dj_profile)
                referred_wallet.total_earnings = F('total_earnings') + referral.referred_bonus
                referred_wallet.pending_earnings = F('pending_earnings') + referral.referred_bonus
                referred_wallet.save(update_fields=['total_earnings', 'pending_earnings'])
                
                LedgerEntry.objects.create(
                    wallet=referred_wallet,
                    amount=referral.referred_bonus,
                    entry_type='credit',
                    description='First sale bonus! 🎉',
                    metadata={'type': 'first_sale_bonus'}
                )
                referral.referred_paid = True
            
            referral.first_sale_achieved = True
            referral.save()


class DJMilestoneReward(models.Model):
    """Milestone rewards for DJ retention."""
    MILESTONES = (
        ('first_track', 'First Track Uploaded'),
        ('first_sale', 'First Sale'),
        ('10_sales', '10 Sales'),
        ('50_sales', '50 Sales'),
        ('100_sales', '100 Sales'),
        ('1000_earnings', '₹1000 Earned'),
        ('5000_earnings', '₹5000 Earned'),
        ('10000_earnings', '₹10000 Earned'),
    )
    
    REWARDS = {
        'first_track': Decimal('50.00'),   # Welcome bonus
        'first_sale': Decimal('25.00'),
        '10_sales': Decimal('100.00'),
        '50_sales': Decimal('250.00'),
        '100_sales': Decimal('500.00'),
        '1000_earnings': Decimal('50.00'),
        '5000_earnings': Decimal('150.00'),
        '10000_earnings': Decimal('300.00'),
    }
    
    dj = models.ForeignKey('accounts.DJProfile', on_delete=models.CASCADE, related_name='milestone_rewards')
    milestone = models.CharField(max_length=50, choices=MILESTONES)
    reward_amount = models.DecimalField(max_digits=10, decimal_places=2)
    credited = models.BooleanField(default=False)
    credited_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('dj', 'milestone')
    
    @classmethod
    def check_and_award(cls, dj_profile):
        """Check all milestones and award any newly achieved."""
        from apps.commerce.models import Purchase, DJWallet
        
        # Get stats
        sales_count = Purchase.objects.filter(seller=dj_profile, status='paid').count()
        wallet = DJWallet.objects.filter(dj=dj_profile).first()
        total_earnings = wallet.total_earnings if wallet else Decimal('0')
        track_count = dj_profile.tracks.filter(is_deleted=False).count()
        
        awarded = []
        
        # Check each milestone
        milestones_to_check = [
            ('first_track', track_count >= 1),
            ('first_sale', sales_count >= 1),
            ('10_sales', sales_count >= 10),
            ('50_sales', sales_count >= 50),
            ('100_sales', sales_count >= 100),
            ('1000_earnings', total_earnings >= 1000),
            ('5000_earnings', total_earnings >= 5000),
            ('10000_earnings', total_earnings >= 10000),
        ]
        
        for milestone, achieved in milestones_to_check:
            if achieved and not cls.objects.filter(dj=dj_profile, milestone=milestone).exists():
                reward = cls.objects.create(
                    dj=dj_profile,
                    milestone=milestone,
                    reward_amount=cls.REWARDS[milestone]
                )
                cls._credit_reward(reward)
                awarded.append(milestone)
        
        return awarded
    
    @classmethod
    def _credit_reward(cls, reward):
        """Credit milestone reward to DJ wallet."""
        with transaction.atomic():
            from apps.commerce.models import DJWallet, LedgerEntry
            from django.db.models import F
            
            wallet, _ = DJWallet.objects.get_or_create(dj=reward.dj)
            wallet.total_earnings = F('total_earnings') + reward.reward_amount
            wallet.pending_earnings = F('pending_earnings') + reward.reward_amount
            wallet.save(update_fields=['total_earnings', 'pending_earnings'])
            
            LedgerEntry.objects.create(
                wallet=wallet,
                amount=reward.reward_amount,
                entry_type='credit',
                description=f'Milestone reward: {reward.get_milestone_display()} 🏆',
                metadata={'type': 'milestone_reward', 'milestone': reward.milestone}
            )
            
            reward.credited = True
            reward.credited_at = timezone.now()
            reward.save()


class DJPromoCode(models.Model):
    """Promotional codes for reduced commission periods."""
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField()
    
    # Commission discount (e.g., 5 = 5% off, so 15% becomes 10%)
    commission_discount = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('5.00'))
    
    # Validity
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    max_uses = models.IntegerField(default=100)
    times_used = models.IntegerField(default=0)
    
    # Targeting
    new_djs_only = models.BooleanField(default=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    @classmethod
    def generate_code(cls, prefix='MIX'):
        """Generate unique promo code."""
        return f"{prefix}{secrets.token_hex(4).upper()}"
    
    def is_valid(self):
        """Check if promo code is currently valid."""
        now = timezone.now()
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_until and
            self.times_used < self.max_uses
        )
    
    def apply_to_dj(self, dj_profile):
        """Apply promo code to a DJ."""
        if not self.is_valid():
            return False, "Promo code is no longer valid"
        
        if self.new_djs_only:
            # Check if DJ joined within last 30 days
            if (timezone.now() - dj_profile.created_at).days > 30:
                return False, "This code is for new DJs only"
        
        # Create promo application record
        DJPromoApplication.objects.create(
            dj=dj_profile,
            promo=self,
            commission_discount=self.commission_discount,
            expires_at=self.valid_until
        )
        
        self.times_used += 1
        self.save(update_fields=['times_used'])
        
        return True, f"Promo applied! You get {self.commission_discount}% off commission until {self.valid_until.strftime('%b %d, %Y')}"


class DJPromoApplication(models.Model):
    """Track which DJs have applied which promo codes."""
    dj = models.ForeignKey('accounts.DJProfile', on_delete=models.CASCADE, related_name='promo_applications')
    promo = models.ForeignKey(DJPromoCode, on_delete=models.CASCADE)
    commission_discount = models.DecimalField(max_digits=5, decimal_places=2)
    applied_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        unique_together = ('dj', 'promo')


class DJOnboardingProgress(models.Model):
    """Track DJ onboarding completion for conversion optimization."""
    dj = models.OneToOneField('accounts.DJProfile', on_delete=models.CASCADE, related_name='onboarding_progress')
    
    # Steps
    profile_completed = models.BooleanField(default=False)
    bank_details_added = models.BooleanField(default=False)
    first_track_uploaded = models.BooleanField(default=False)
    pricing_set = models.BooleanField(default=False)
    store_customized = models.BooleanField(default=False)
    
    # Completion tracking
    completion_percent = models.IntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Reminder tracking
    last_reminder_sent = models.DateTimeField(null=True, blank=True)
    reminders_sent = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def update_progress(self):
        """Calculate completion percentage."""
        steps = [
            self.profile_completed,
            self.bank_details_added,
            self.first_track_uploaded,
            self.pricing_set,
            self.store_customized,
        ]
        completed = sum(1 for s in steps if s)
        self.completion_percent = int((completed / len(steps)) * 100)
        
        if self.completion_percent == 100 and not self.completed_at:
            self.completed_at = timezone.now()
            # Trigger completion bonus
            DJWelcomeBonus.credit_welcome_bonus(self.dj)
        
        self.save()
        return self.completion_percent
