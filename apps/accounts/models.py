from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _


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
    username = None
    email = models.EmailField(_('email address'), unique=True)

    ROLE_CHOICES = (
        ('user', 'User'),      # Listener/Buyer [Spec §3.1]
        ('dj', 'DJ'),          # Partner Artist [Spec §3.2]
        ('admin', 'Admin'),    # Platform Admin [Spec §3.3]
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=255)
    avatar_url = models.URLField(max_length=500, null=True, blank=True)
    is_banned = models.BooleanField(default=False)
    is_frozen = models.BooleanField(default=False)  # Admin freeze [Spec §11]
    last_active_at = models.DateTimeField(null=True, blank=True)  # Auto-expire after 12 months [Spec §10]
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name or self.user.email


class DJProfile(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('banned', 'Banned'),
    )

    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='dj_profile')
    dj_name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)  # Vanity URL: mixmint.site/djname [Spec §9]
    bio = models.TextField(null=True, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payout_details = models.JSONField(default=dict, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    popularity_score = models.IntegerField(default=0)
    genres = models.JSONField(default=list, blank=True)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    store_paused = models.BooleanField(default=False)  # DJ can pause store [Spec §3.2]
    application_fee_paid = models.BooleanField(default=False)  # ₹99 fee [Spec §6]
    legal_agreement_accepted = models.BooleanField(default=False)  # Mandatory [Spec §6]
    is_verified_dj = models.BooleanField(default=False)  # Verified DJ badge [Spec P2 §2]
    is_pro_dj = models.BooleanField(default=False)  # Pro Plan: 8% commission [Spec P3 §1.5]
    custom_domain = models.CharField(max_length=255, null=True, blank=True)  # Pro feature
    ad_exposure_reduction = models.BooleanField(default=False)  # Pro feature [Spec P3 §1.2]
    
    # 2FA for payouts [Spec P2 §11, P3 §3.2]
    payout_otp_secret = models.CharField(max_length=32, null=True, blank=True)
    payout_otp_timestamp = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.dj_name


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
