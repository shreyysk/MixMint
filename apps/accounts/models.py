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
    store_paused = models.BooleanField(default=False)

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


class DJApplication(models.Model):
    """DJ application workflow [Spec P2 §2]"""

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='dj_application')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    paid_application_fee = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(null=True, blank=True)
