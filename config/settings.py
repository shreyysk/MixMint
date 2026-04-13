import os
from pathlib import Path
import environ
from django.utils import timezone
import datetime

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False)
)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Quick-start development settings - unsuitable for production
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'storages',
    
    # Local apps
    'apps.accounts',
    'apps.tracks',
    'apps.albums',
    'apps.commerce',
    'apps.payments',
    'apps.downloads',
    'apps.admin_panel',
    'apps.social',    # Stub: wishlists + follows (no gamification) [Spec §6]
    'apps.rewards',   # Stub: referral tracking only [Spec §8]
    'social_django',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Custom MixMint Middleware [Spec §11, §13, P2 §15]
    'apps.accounts.middleware.MaintenanceModeMiddleware',
    'apps.accounts.middleware.BlacklistMiddleware',
    'apps.accounts.middleware.IPSessionMiddleware',
    'apps.accounts.middleware.InactivityMiddleware',  # Updates last_active_at for 12-month expiry [Spec §10]
    'apps.accounts.middleware.ReferralMiddleware',
    'apps.admin_panel.middleware.FraudDetectionMiddleware',
    # Phase 3 Security Middleware [EX-01.03, EX-02.01, EX-02.02]
    'apps.core.security_middleware.SecurityMiddleware',
    'apps.core.security_middleware.AccountVelocityMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.admin_panel.context_processors.global_settings',
                'apps.core.context_processors.seo_context',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': env.db('DATABASE_URL', default='sqlite:///db.sqlite3')
}

# Auth & JWT Configuration
AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

# Supabase Auth [Spec §13]
# ----------------------
# Google login and all authentication are handled by Supabase on the frontend.
# Django acts as the backend service verifying the JWTs issued by Supabase.
# SUPABASE_URL and SUPABASE_KEY are handled by the client.

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day',
        'search': '20/minute',  # Custom rate for intensive queries [Fix 16]
        'burst': '10/minute',   # Mitigation for scrapers
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
LANGUAGES = [
    ('en', 'English'),
    ('hi', 'Hindi'),
]
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Cloudflare R2 / S3 Config [Gap 07]
AWS_ACCESS_KEY_ID = env('R2_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = env('R2_SECRET_ACCESS_KEY', default='')
AWS_S3_ENDPOINT_URL = env('R2_ENDPOINT', default='')
AWS_S3_REGION_NAME = 'auto'

# Separate buckets for raw vs public [Spec Phase 1 Section B §4]
R2_PRIVATE_BUCKET = env('R2_PRIVATE_BUCKET', default='mixmint-raw')
R2_PUBLIC_BUCKET = env('R2_PUBLIC_BUCKET', default='mixmint-public')
AWS_STORAGE_BUCKET_NAME = R2_PRIVATE_BUCKET # Default to private

AWS_S3_CUSTOM_DOMAIN = env('R2_PUBLIC_URL', default='').replace('https://', '').replace('http://', '')

# File Standards [Gap 10]
SUPPORTED_AUDIO_FORMATS = ['mp3', 'wav', 'aiff', 'flac']
MAX_UPLOAD_SIZE_MB = 200 # 200MB limit for raw tracks

# Razorpay Config
RAZORPAY_KEY_ID = env('RAZORPAY_KEY_ID', default='')
RAZORPAY_KEY_SECRET = env('RAZORPAY_KEY_SECRET', default='')

# PhonePe Config [Spec P1 Section A]
PHONEPE_MERCHANT_ID = env('PHONEPE_MERCHANT_ID', default='PGTESTPAYUAT')
PHONEPE_SALT_KEY = env('PHONEPE_SALT_KEY', default='099eb0cd-02cf-4e2a-8aca-3e6c6aff0399')
PHONEPE_SALT_INDEX = env('PHONEPE_SALT_INDEX', default='1')
# Environment-based base URL
ENVIRONMENT = env('ENVIRONMENT', default='development')
if ENVIRONMENT == 'production':
    PHONEPE_BASE_URL = 'https://api.phonepe.com/apis/hermes'
else:
    # Sandbox/Test URL
    PHONEPE_BASE_URL = 'https://api-preprod.phonepe.com/apis/pg-sandbox'

BASE_URL = env('BASE_URL', default='http://localhost:8000')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS
CORS_ALLOW_ALL_ORIGINS = True  # Update for production

# Resend Email Config [Spec Tech Stack]
RESEND_API_KEY = env('RESEND_API_KEY', default='')
FROM_EMAIL = env('FROM_EMAIL', default='noreply@mixmint.site')

# Celery Config [Spec Tech Stack]
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')

# Platform Constants
PLATFORM_LAUNCH_DATE = timezone.datetime(2026, 3, 1, tzinfo=datetime.timezone.utc)
PLATFORM_COMMISSION_RATE = 0.15  # 15% [Spec P3 §1.1]
PRO_DJ_COMMISSION_RATE = 0.08    # 8% for Pro DJs [Spec P3 §1.5]
DJ_AD_REVENUE_SHARE = 0.15       # 15% ad revenue to DJ [Spec P3 §1.2]
CHECKOUT_FEE = 5.00              # ₹5 service fee [Spec P3 §1.3]
MIN_PAYOUT_THRESHOLD = 500.00    # ₹500 [Spec P2 §9]
DJ_APPLICATION_FEE = 99.00       # ₹99 [Spec §7]
MIN_TRACK_PRICE = 29.00          # ₹29 [CP-06.02 FIX]
MIN_ALBUM_PRICE = 49.00          # ₹49 [Spec §3.2]
DOWNLOAD_TOKEN_EXPIRY_MINUTES = 5  # [Spec §4.5]
IP_LOCK_DAYS = 2                 # [Spec §4.3]
MAX_DOWNLOAD_ATTEMPTS = 3       # [Spec §4.2]
INACTIVE_ACCOUNT_THRESHOLD_MONTHS = 12 # [Spec §10]

# Auth URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'home'

# Active Payment Gateway Selection (Lazy loaded to avoid import errors)
# The actual gateway is imported when first accessed via get_payment_gateway()
def get_payment_gateway():
    """Get the active payment gateway based on environment."""
    if ENVIRONMENT == 'production':
        from apps.payments.phonepe import PhonePeGateway
        return PhonePeGateway()
    else:
        from apps.payments.phonepe import PhonePeGateway
        # Use PhonePe in dev too for consistency
        return PhonePeGateway()

# For backwards compatibility - lazy loaded
class LazyGateway:
    _gateway = None
    
    def __getattr__(self, name):
        if self._gateway is None:
            self._gateway = get_payment_gateway()
        return getattr(self._gateway, name)

ACTIVE_GATEWAY = LazyGateway()

# Production Safety Guards (only run in production)
if ENVIRONMENT == 'production':
    _gateway = get_payment_gateway()
    from apps.payments.phonepe import PhonePeGateway
    assert isinstance(_gateway, PhonePeGateway), "Production must use PhonePeGateway"
    assert 'preprod' not in PHONEPE_BASE_URL, "Production is using PhonePe SANDBOX URL"

# Vercel Configuration [Phase 1 Section C Fix 02]
VERCEL_TOKEN = os.getenv('VERCEL_TOKEN')
VERCEL_PROJECT_ID = os.getenv('VERCEL_PROJECT_ID')
VERCEL_TEAM_ID = os.getenv('VERCEL_TEAM_ID') # Optional

# Social Auth Google Configuration
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = env('GOOGLE_CLIENT_ID', default='')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = env('GOOGLE_CLIENT_SECRET', default='')

# Social Auth Pipeline
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)

SOCIAL_AUTH_URL_NAMESPACE = 'social'

# Conditionally add django.contrib.postgres when using PostgreSQL
if DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
    INSTALLED_APPS.append('django.contrib.postgres')
