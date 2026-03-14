from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
import uuid


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField(_('email address'), unique=True)

    email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()



class DJProfile(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('banned', 'Banned'),
    )

    profile = models.OneToOneField('Profile', on_delete=models.CASCADE, related_name='dj_profile')
    dj_name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)  # Vanity URL: mixmint.site/djname [Spec §9]
    bio = models.TextField(null=True, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payout_details = models.JSONField(default=dict, blank=True)
    bank_account_number = models.CharField(max_length=50, null=True, blank=True)
    bank_ifsc_code = models.CharField(max_length=20, null=True, blank=True)
    upi_id = models.CharField(max_length=100, null=True, blank=True)
    pan_number = models.CharField(max_length=10, null=True, blank=True)
    is_pan_verified = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False) # Top seller badge
    verified_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    popularity_score = models.IntegerField(default=0)
    genres = models.JSONField(default=list, blank=True)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    custom_domain = models.CharField(max_length=255, null=True, blank=True)  # Pro feature
    ad_exposure_reduction = models.BooleanField(default=False)  # Pro feature [Spec P3 §1.2]
    
    # [Missing Item 02] Dynamic Ad Floor Pricing
    weekly_views = models.PositiveIntegerField(default=0)
    ad_floor_cpm = models.DecimalField(max_digits=10, decimal_places=2, default=50.00)
    overage_enabled = models.BooleanField(default=True)
    custom_storage_quota_mb = models.BigIntegerField(null=True, blank=True)
    
    # 2FA for payouts [Spec P2 §11, P3 §3.2]
    payout_otp_secret = models.CharField(max_length=32, null=True, blank=True)
    payout_otp_timestamp = models.DateTimeField(null=True, blank=True)

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Onboarding Wizard [Fix 07]
    onboarding_step = models.CharField(max_length=50, default='profile_setup') # profile_setup, payout_setup, first_track, completed
    is_onboarding_complete = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.dj_name

    def save(self, *args, **kwargs):
        """Auto-generate slug if missing [Gap 06]."""
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.dj_name)
            # Ensure uniqueness
            original_slug = self.slug
            counter = 1
            while DJProfile.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def soft_delete(self):
        """Soft-delete DJ profile and move funds to escrow [Fix 05]."""
        from apps.commerce.models import DJWallet
        wallet, _ = DJWallet.objects.get_or_create(dj=self)
        
        # Transfer available funds to escrow
        if wallet.available_for_payout > 0:
            wallet.escrow_amount += wallet.available_for_payout
            wallet.available_for_payout = 0
            wallet.save()
            
        self.is_deleted = True
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.status = 'rejected' # Mark as inactive
        self.save()


class Profile(models.Model):
    ROLE_CHOICES = (
        ('user', 'User'),      # Listener/Buyer [Spec §3.1]
        ('dj', 'DJ'),          # Partner Artist [Spec §3.2]
        ('admin', 'Admin'),    # Platform Admin [Spec §3.3]
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', primary_key=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    full_name = models.CharField(max_length=255)
    avatar_url = models.URLField(max_length=500, null=True, blank=True)

    # DJ flags stored on profile (canonical) [Spec P2 profiles]
    is_verified_dj = models.BooleanField(default=False)
    is_pro_dj = models.BooleanField(default=False)
    pro_plan_type = models.CharField(max_length=10, choices=(('monthly', 'Monthly'), ('annual', 'Annual')), null=True, blank=True)
    pro_started_at = models.DateTimeField(null=True, blank=True)
    pro_expires_at = models.DateTimeField(null=True, blank=True)
    pro_trial_ends_at = models.DateTimeField(null=True, blank=True)
    pro_grace_ends_at = models.DateTimeField(null=True, blank=True)
    
    storage_quota_mb = models.BigIntegerField(default=3072) # 3GB default

    store_paused = models.BooleanField(default=False)

    is_banned = models.BooleanField(default=False)
    is_frozen = models.BooleanField(default=False)  # Admin freeze [Spec §11]
    # Referral context [Imp 15]
    referred_by = models.ForeignKey('accounts.DJProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name or self.user.email

class DJAnnouncement(models.Model):
    """Imp 14: DJ updates and announcements for storefront."""
    dj = models.ForeignKey(DJProfile, on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.dj.dj_name}: {self.title}"

class AmbassadorCode(models.Model):
    """Imp 15: DJ Ambassador (referral) codes."""
    dj = models.OneToOneField(DJProfile, on_delete=models.CASCADE, related_name='ambassador_code')
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    referral_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.dj.dj_name} ({self.code})"


class LoginHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(null=True, blank=True)
    location_data = models.JSONField(default=dict, blank=True)
    is_suspicious = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class UserDevice(models.Model):
    STATUS_CHOICES = (
        ('authorized', 'Authorized'),
        ('revoked', 'Revoked'),
        ('banned', 'Banned'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    fingerprint = models.CharField(max_length=255)
    label = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='authorized')
    last_ip = models.GenericIPAddressField(null=True, blank=True)
    last_active_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'fingerprint')


class DJApplication(models.Model):
    """DJ application workflow [Spec P2 §2]"""

    STATUS_CHOICES = (
        ('pending_payment', 'Pending Payment'),
        ('pending_review', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='dj_application')
    dj_name = models.CharField(max_length=255, null=True, blank=True)
    genres = models.JSONField(default=list, blank=True)
    bio = models.TextField(null=True, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    why_mixmint = models.TextField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_payment')
    paid_application_fee = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(null=True, blank=True)

class Waitlist(models.Model):
    """Imp 10: Launch Waitlist System."""
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    is_dj = models.BooleanField(default=False)
    source = models.CharField(max_length=100, default='homepage')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

class DJPageView(models.Model):
    """Missing Item 02: Storefront and track views per DJ"""
    dj = models.ForeignKey('DJProfile', on_delete=models.CASCADE, related_name='page_views')
    page_type = models.CharField(max_length=50) # 'storefront', 'track_page'
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)



class IPBlacklist(models.Model):
    """Missing Item 03: Hard IP / Device Blacklist"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=10, choices=(('ip', 'IP Address'), ('cidr', 'CIDR Range'), ('device', 'Device Fingerprint')))
    value = models.CharField(max_length=100)
    reason = models.TextField(null=True, blank=True)
    added_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='blacklisted_ips')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('type', 'value')

    def __str__(self):
        return f"{self.type}: {self.value}"



# ============================================
# PUSH NOTIFICATIONS & A/B TESTING MODELS
# ============================================

class PushSubscription(models.Model):
    """Store user's push notification subscriptions."""
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.TextField()
    p256dh_key = models.TextField()
    auth_key = models.TextField()
    device_type = models.CharField(max_length=20, default='web')
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('user', 'endpoint')


class NotificationPreference(models.Model):
    """User notification preferences."""
    user = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='notification_prefs')
    email_sales = models.BooleanField(default=True)
    email_payouts = models.BooleanField(default=True)
    email_milestones = models.BooleanField(default=True)
    email_marketing = models.BooleanField(default=False)
    push_sales = models.BooleanField(default=True)
    push_new_followers = models.BooleanField(default=True)
    push_milestones = models.BooleanField(default=True)
    push_promotions = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)


class InAppNotification(models.Model):
    """In-app notification storage."""
    TYPES = (
        ('sale', 'New Sale'),
        ('payout', 'Payout'),
        ('milestone', 'Milestone'),
        ('referral', 'Referral'),
        ('system', 'System'),
        ('promo', 'Promotion'),
    )
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='in_app_notifications')
    notification_type = models.CharField(max_length=20, choices=TYPES)
    title = models.CharField(max_length=100)
    message = models.TextField()
    data = models.JSONField(default=dict)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']


class Experiment(models.Model):
    """A/B test experiment definition."""
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
    )
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    target_audience = models.CharField(max_length=50, default='all')
    traffic_percentage = models.IntegerField(default=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def is_active(self):
        if self.status != 'running':
            return False
        now = timezone.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True


class Variant(models.Model):
    """Variant within an experiment."""
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=50)
    weight = models.IntegerField(default=50)
    config = models.JSONField(default=dict)
    
    class Meta:
        unique_together = ('experiment', 'name')


class UserExperiment(models.Model):
    """Track which variant a user is assigned to."""
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='ab_experiments')
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'experiment')


class ExperimentEvent(models.Model):
    """Track events/conversions for experiments."""
    user_experiment = models.ForeignKey(UserExperiment, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=50)
    value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
