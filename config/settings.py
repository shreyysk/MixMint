import os
import logging
from pathlib import Path
import environ
from django.utils import timezone
import datetime

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# Quick-start development settings - unsuitable for production
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["testserver", "localhost", "127.0.0.1"])

# Environment detection (must be before production block)
# Hosted platforms default to production so a missing ENVIRONMENT var can't ship dev settings
# (open CORS, insecure cookies) to real users.
_ON_HOST = any(os.environ.get(k) for k in ("RENDER", "RAILWAY_ENVIRONMENT", "VERCEL", "DYNO"))
ENVIRONMENT = env("ENVIRONMENT", default="production" if _ON_HOST else "development")

# Number of reverse proxies in front of Django that append to X-Forwarded-For.
# Render / Railway / Vercel = 1; Cloudflare in front of them = 2; local dev = 0.
# Used by apps.core.net.get_client_ip — never trust the left-most XFF entry.
NUM_PROXIES = env.int("NUM_PROXIES", default=1 if ENVIRONMENT == "production" else 0)

if ENVIRONMENT == "production":
    if not SECRET_KEY or SECRET_KEY.startswith("django-insecure"):
        raise ValueError("SECRET_KEY must be a long random value in production")
    if len(SECRET_KEY) < 50:
        logging.getLogger("mixmint").warning("SECRET_KEY is shorter than 50 characters; rotate it to a longer value.")
if ENVIRONMENT == "production" and DEBUG:
    raise ValueError("DEBUG must be False in production")

# Production Safety Assertion - ALLOWED_HOSTS must be configured
if ENVIRONMENT == "production" and not ALLOWED_HOSTS:
    raise ValueError("ALLOWED_HOSTS must be configured in production")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    # Third-party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "storages",
    "django_celery_beat",
    "csp",
    "drf_spectacular",
    # Local apps
    "apps.accounts",
    "apps.tracks",
    "apps.albums",
    "apps.commerce",
    "apps.payments",
    "apps.downloads",
    "apps.admin_panel",
    "apps.core",
    "social_django",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    # Custom MixMint Middleware [Spec §11, §13, P2 §15]
    "apps.accounts.middleware.MaintenanceModeMiddleware",
    "apps.accounts.middleware.BlacklistMiddleware",
    "apps.accounts.middleware.IPSessionMiddleware",
    "apps.accounts.middleware.InactivityMiddleware",  # Updates last_active_at for 12-month expiry [Spec §10]
    "apps.accounts.middleware.ReferralMiddleware",
    "apps.admin_panel.middleware.FraudDetectionMiddleware",
    # Phase 3 Security Middleware [EX-01.03, EX-02.01, EX-02.02]
    "apps.core.security_middleware.SecurityMiddleware",
    "apps.core.security_middleware.AccountVelocityMiddleware",
    "apps.accounts.social_middleware.MixMintSocialAuthExceptionMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.admin_panel.context_processors.global_settings",
                "apps.admin_panel.context_processors.admin_nav",
                "apps.core.context_processors.seo_context",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
DATABASES = {"default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3")}
# Supabase / PgBouncer *transaction* pooler (port 6543): server-side cursors and
# persistent connections don't survive transaction pooling, so turn both off.
if str(DATABASES["default"].get("PORT", "")) == "6543" or env.bool("DB_TRANSACTION_POOLER", default=False):
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
    DATABASES["default"]["CONN_MAX_AGE"] = 0

# Auth & JWT Configuration
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = (
    "social_core.backends.google.GoogleOAuth2",
    "django.contrib.auth.backends.ModelBackend",
)

# Supabase Auth [Spec §13]
# ----------------------
# Google login and all authentication are handled by Supabase on the frontend.
# Django acts as the backend service verifying the JWTs issued by Supabase.
# SUPABASE_URL and SUPABASE_KEY are handled by the client.

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "apps.accounts.permissions.IsNotBanned",
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # Public browsing hits the API constantly; keep limits per hour, not per day.
        "anon": "600/hour",
        "user": "3000/hour",
        "search": "60/min",
        "auth": "10/min",  # For login/register endpoints
        "payment": "20/hour",  # For checkout endpoints
        "download": "30/hour",  # For download endpoints
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "MixMint 2.0 API",
    "DESCRIPTION": "Premium Marketplace for DJ Tool Kits & Exclusive Edits",
    "VERSION": "2.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1/",
    "COMPONENT_SPLIT_REQUEST": True,
    "COMPONENT_NO_READ_ONLY_REQUIRED": True,
    "SECURITY": [{"BearerAuth": []}],
    "COMPONENT_SECURITY_SCHEMES": {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
    },
    "TAGS": [
        {"name": "accounts", "description": "User authentication, profiles, DJ applications"},
        {"name": "tracks", "description": "Track management, previews, metadata"},
        {"name": "albums", "description": "Album packs, ZIP processing"},
        {"name": "commerce", "description": "Purchases, wallets, payouts, cart"},
        {"name": "payments", "description": "PhonePe + Razorpay checkout, webhooks"},
        {"name": "downloads", "description": "Secure download tokens, streaming"},
        {"name": "admin", "description": "Admin panel: moderation, settings, analytics"},
        {"name": "platform", "description": "Core platform: notifications, A/B tests, mobile API"},
    ],
    "SERVERS": [
        {"url": "https://mixmint.site/api/v1", "description": "Production"},
        {"url": "http://localhost:8000/api/v1", "description": "Local Development"},
    ],
    "ENUM_NAME_OVERRIDES": {
        "ContentTypeEnum": "apps.commerce.models.Purchase.CONTENT_TYPES",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": datetime.timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": datetime.timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Logging Configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "console_prod": {
            "level": "INFO",
            "filters": ["require_debug_false"],
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "console_prod"],
            "level": "INFO",
            "propagate": True,
        },
        "django.request": {
            "handlers": ["console", "console_prod"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console", "console_prod"],
            "level": "INFO",
            "propagate": True,
        },
        "mixmint": {
            "handlers": ["console", "console_prod"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

# Sentry Configuration
SENTRY_DSN = env("SENTRY_DSN", default="")
# Sentry Event Scrubber


def _scrub_sentry_event(event, hint):
    """
    Remove sensitive data from Sentry events before sending.
    """
    sensitive_keys = [
        "password",
        "secret",
        "token",
        "key",
        "csrf",
        "authorization",
        "cookie",
        "session",
        "jwt",
        "razorpay",
        "phonepe",
        "salt",
        "api_key",
    ]

    def scrub_dict(d):
        if isinstance(d, dict):
            for k in list(d.keys()):
                if any(s in k.lower() for s in sensitive_keys):
                    d[k] = "[REDACTED]"
                elif isinstance(d[k], (dict, list)):
                    scrub_dict(d[k])
        elif isinstance(d, list):
            for item in d:
                scrub_dict(item)

    # Scrub request data
    if "request" in event:
        req = event["request"]
        if "headers" in req:
            scrub_dict(req["headers"])
        if "cookies" in req:
            req["cookies"] = "[REDACTED]"
        if "data" in req:
            scrub_dict(req["data"])

    # Scrub extra data
    if "extra" in event:
        scrub_dict(event["extra"])

    # Scrub user PII if present
    if "user" in event and isinstance(event["user"], dict):
        if "email" in event["user"]:
            event["user"]["email"] = "[REDACTED]"
        if "ip_address" in event["user"]:
            event["user"]["ip_address"] = "[REDACTED]"

    return event


if SENTRY_DSN and ENVIRONMENT == "production":
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR,
    )
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            sentry_logging,
        ],
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        send_default_pii=False,
        environment=ENVIRONMENT,
        before_send=lambda event, hint: _scrub_sentry_event(event, hint),
    )

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.accounts.validators.StrongPasswordValidator"},
]

# Internationalization (English only)
LANGUAGE_CODE = "en-us"
LANGUAGES = [
    ("en", "English"),
]
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
# Don't crash if a referenced static file is missing (e.g. conditional template assets)
WHITENOISE_MANIFEST_STRICT = False

# Django 5.1+ STORAGES setting (overrides STATICFILES_STORAGE)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Cloudflare R2 / S3 Config [Gap 07]
AWS_ACCESS_KEY_ID = env("R2_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("R2_SECRET_ACCESS_KEY", default="")
AWS_S3_ENDPOINT_URL = env("R2_ENDPOINT", default="")
AWS_S3_REGION_NAME = "auto"

# Separate buckets for raw vs public [Spec Phase 1 Section B §4]
# R2_BUCKET_NAME is accepted as an alias (render.yaml / older .env files use it).
R2_PRIVATE_BUCKET = env("R2_PRIVATE_BUCKET", default=env("R2_BUCKET_NAME", default="mixmint-raw"))
R2_PUBLIC_BUCKET = env("R2_PUBLIC_BUCKET", default="mixmint-public")
R2_PUBLIC_URL = env("R2_PUBLIC_URL", default="")
AWS_STORAGE_BUCKET_NAME = R2_PRIVATE_BUCKET  # Default to private

AWS_S3_CUSTOM_DOMAIN = env("R2_PUBLIC_URL", default="").replace("https://", "").replace("http://", "")

# File Standards [Gap 10]
SUPPORTED_AUDIO_FORMATS = ["mp3", "wav", "aiff", "flac"]
MAX_UPLOAD_SIZE_MB = 200  # 200MB limit for raw tracks

# Razorpay Config
RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID", default="")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET", default="")
# Webhook secret configured in Razorpay Dashboard -> Webhooks (different from the API key secret).
RAZORPAY_WEBHOOK_SECRET = env("RAZORPAY_WEBHOOK_SECRET", default="")
# Razorpay test keys (rzp_test_...) = sandbox: no real money moves. Going live is only an
# env change: swap in rzp_live_ keys + the live webhook secret and redeploy.
PAYMENTS_TEST_MODE = RAZORPAY_KEY_ID.startswith("rzp_test_")

# PhonePe Config [Spec P1 Section A]
PHONEPE_MERCHANT_ID = env("PHONEPE_MERCHANT_ID", default="")
PHONEPE_SALT_KEY = env("PHONEPE_SALT_KEY", default="")
PHONEPE_SALT_INDEX = env("PHONEPE_SALT_INDEX", default="1")
# Environment-based base URL
if ENVIRONMENT == "production":
    PHONEPE_BASE_URL = "https://api.phonepe.com/apis/hermes"
else:
    # Sandbox/Test URL
    PHONEPE_BASE_URL = "https://api-preprod.phonepe.com/apis/pg-sandbox"

BASE_URL = env("BASE_URL", default="http://localhost:8000")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS
if ENVIRONMENT == "production":
    CORS_ALLOWED_ORIGINS = env.list(
        "CORS_ALLOWED_ORIGINS",
        default=[
            "https://mix-mint.vercel.app",
            "https://mixmint.site",
        ],
    )
    CORS_ALLOW_ALL_ORIGINS = False
else:
    CORS_ALLOW_ALL_ORIGINS = True

# Resend Email Config [Spec Tech Stack]
RESEND_API_KEY = env("RESEND_API_KEY", default="")
FROM_EMAIL = env("FROM_EMAIL", default="noreply@mixmint.site")
DEFAULT_FROM_EMAIL = FROM_EMAIL
SERVER_EMAIL = FROM_EMAIL
# All Django mail (password reset, EmailService) goes through Resend when a key is set.
if RESEND_API_KEY:
    EMAIL_BACKEND = "apps.core.resend_backend.ResendEmailBackend"
elif DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Cache: set CACHE_URL=redis://... in production so rate limits, fraud counters and
# download slots are shared across gunicorn workers. Falls back to per-process memory.
CACHES = {"default": env.cache("CACHE_URL", default="locmemcache://mixmint")}

# Shared secret for worker-free cron endpoints (/cron/<job>/) + one-off guards.
CRON_SECRET = env("CRON_SECRET", default="")

# Celery Config [Spec Tech Stack]
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# Free-tier / serverless mode: run background tasks inline (no Redis/worker needed).
# Set CELERY_TASK_ALWAYS_EAGER=True on hosts like Render-free; scheduled jobs
# are then triggered by cron-job.org hitting /cron/<job>/ instead of beat.
# On Vercel (serverless, no workers possible) eager mode is the safe default.
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER", default=os.environ.get("VERCEL") == "1")

# Platform Constants
PLATFORM_LAUNCH_DATE = timezone.datetime(2026, 3, 1, tzinfo=datetime.timezone.utc)
PLATFORM_COMMISSION_RATE = 0.15  # 15% [Spec P3 §1.1]
PRO_DJ_COMMISSION_RATE = 0.08  # 8% for Pro DJs [Spec P3 §1.5]
DJ_AD_REVENUE_SHARE = 0.15  # 15% ad revenue to DJ [Spec P3 §1.2]
CHECKOUT_FEE = 5.00  # ₹5 service fee [Spec P3 §1.3]
MIN_PAYOUT_THRESHOLD = 500.00  # ₹500 [Spec P2 §9]
DJ_APPLICATION_FEE = 99.00  # ₹99 [Spec §7]
MIN_TRACK_PRICE = 29.00  # ₹29 [CP-06.02 FIX]
MIN_ALBUM_PRICE = 49.00  # ₹49 [Spec §3.2]
DOWNLOAD_TOKEN_EXPIRY_MINUTES = 5  # [Spec §4.5]
# How files reach the buyer after the token checks pass:
#   proxy     - stream through Django (byte + SHA-256 verified). Best on always-on servers.
#   auto      - proxy small files, hand large ones (> DOWNLOAD_PROXY_MAX_MB) to a short-lived R2
#               signed URL so serverless time/size limits (Vercel) never cut a download off.
#   presigned - always hand off to a short-lived R2 signed URL.
DOWNLOAD_DELIVERY = env("DOWNLOAD_DELIVERY", default="auto" if os.getenv("VERCEL") else "proxy")
DOWNLOAD_PROXY_MAX_MB = env.int("DOWNLOAD_PROXY_MAX_MB", default=40)
DOWNLOAD_PRESIGN_SECONDS = env.int("DOWNLOAD_PRESIGN_SECONDS", default=120)
IP_LOCK_DAYS = 3  # [Spec §4.3] re-download at 50% after 3-day lock
MAX_DOWNLOAD_ATTEMPTS = 3  # [Spec §4.2]
INACTIVE_ACCOUNT_THRESHOLD_MONTHS = 12  # [Spec §10]

# External-source downloads (DJ Drive/MediaFire link -> MixMint signed endpoint)
EXTERNAL_DOWNLOAD_TOKEN_MINUTES = 15  # lazy-fetch token lifetime
EXTERNAL_DOWNLOAD_MAX_USES = 1  # single-use by default (set 2-3 to allow retry)
EXTERNAL_DOWNLOAD_CACHE_DIR = "external_cache"  # under MEDIA_ROOT
EXTERNAL_DOWNLOAD_MAX_MB = 500  # refuse to cache files larger than this
EXTERNAL_DOWNLOAD_TIMEOUT_SEC = 120  # per-file fetch timeout
DOWNLOAD_EXPIRY_WARNING_HOURS = 10  # "expiring soon" banner threshold on download page
# Google Drive API key (optional quota helper; files stay on DJs' own Drives)
GOOGLE_DRIVE_API_KEY = env("GOOGLE_DRIVE_API_KEY", default="")

# Telegram support bridge (SupportTicket alerts + contact deep link)
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_ADMIN_CHAT_ID = env("TELEGRAM_ADMIN_CHAT_ID", default="")
TELEGRAM_BOT_USERNAME = env("TELEGRAM_BOT_USERNAME", default="")
# Vault channels are normally linked from Telegram (/link singles <code>); these override that.
TELEGRAM_SINGLES_CHANNEL_ID = env("TELEGRAM_SINGLES_CHANNEL_ID", default="")
TELEGRAM_ZIPS_CHANNEL_ID = env("TELEGRAM_ZIPS_CHANNEL_ID", default="")
# Self-hosted Bot API server (raises the 50 MB send / 20 MB fetch limits to 2 GB). Optional.
TELEGRAM_API_BASE = env("TELEGRAM_API_BASE", default="https://api.telegram.org")
# Vault worker (vault_worker/): moves files between R2 and the channels through a Local Bot API Server.
VAULT_WORKER_URL = env("VAULT_WORKER_URL", default="")
VAULT_WORKER_SECRET = env("VAULT_WORKER_SECRET", default="")

# Auth URLs
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "after_login"
LOGOUT_REDIRECT_URL = "home"

# Active payment gateway: DEFAULT_PAYMENT_GATEWAY env var, overridable by the admin
# toggle (SystemSetting "active_payment_gateway"). See apps.payments.utils.get_gateway.
DEFAULT_PAYMENT_GATEWAY = env("DEFAULT_PAYMENT_GATEWAY", default="razorpay")  # 'phonepe' or 'razorpay'


def get_payment_gateway(gateway_name=None):
    """Back-compat wrapper; use apps.payments.utils.get_gateway."""
    from apps.payments.utils import get_gateway

    return get_gateway(gateway_name)


class LazyGateway:
    """Back-compat: resolves the active gateway on every attribute access."""

    def __getattr__(self, name):
        if name.startswith("__"):  # introspection (e.g. Django's debug page) must not build a gateway
            raise AttributeError(name)
        return getattr(get_payment_gateway(), name)

    def __repr__(self):
        return "<LazyGateway>"


# Not exposed as an UPPERCASE setting: Django's debug/error pages introspect every
# setting, and resolving a gateway there crashed error reports when keys were missing.
_active_gateway = LazyGateway()

# Production Safety Guards (only run in production)
if ENVIRONMENT == "production":
    # Allow either gateway in production, but verify configuration
    if DEFAULT_PAYMENT_GATEWAY == "phonepe":
        assert "preprod" not in PHONEPE_BASE_URL, "Production is using PhonePe SANDBOX URL"
    elif DEFAULT_PAYMENT_GATEWAY == "razorpay":
        assert RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET, "Razorpay keys not configured for production"
        if not RAZORPAY_WEBHOOK_SECRET:
            logging.getLogger("mixmint").warning("RAZORPAY_WEBHOOK_SECRET not set: Razorpay webhooks will be rejected.")
        if PAYMENTS_TEST_MODE:
            logging.getLogger("mixmint").warning("Razorpay TEST keys in production: payments are simulated (test-mode banner shown).")

# Vercel Configuration [Phase 1 Section C Fix 02]
VERCEL_TOKEN = os.getenv("VERCEL_TOKEN")
VERCEL_PROJECT_ID = os.getenv("VERCEL_PROJECT_ID")
VERCEL_TEAM_ID = os.getenv("VERCEL_TEAM_ID")  # Optional

# Social Auth Google Configuration
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = env("GOOGLE_CLIENT_ID", default="")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = env("GOOGLE_CLIENT_SECRET", default="")

GOOGLE_LOGIN_ENABLED = bool(SOCIAL_AUTH_GOOGLE_OAUTH2_KEY and SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET)
# Always show Google's account chooser (people with several Google accounts).
SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS = {"prompt": "select_account"}
SOCIAL_AUTH_LOGIN_REDIRECT_URL = "/start/"
SOCIAL_AUTH_LOGIN_ERROR_URL = "/login/"
SOCIAL_AUTH_INACTIVE_USER_URL = "/login/"
SOCIAL_AUTH_RAISE_EXCEPTIONS = False
SOCIAL_AUTH_USER_FIELDS = ["email", "first_name", "last_name"]
SOCIAL_AUTH_PROTECTED_USER_FIELDS = ["email"]
# Redirect URI to register in Google Cloud Console:
#   https://<your-domain>/social-auth/complete/google-oauth2/

# Social Auth Pipeline
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "apps.accounts.social_pipeline.require_verified_email",
    "apps.accounts.social_pipeline.associate_by_verified_email",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
    "apps.accounts.social_pipeline.finish_mixmint_login",
)

SOCIAL_AUTH_URL_NAMESPACE = "social"

# Conditionally add django.contrib.postgres when using PostgreSQL
if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
    INSTALLED_APPS.append("django.contrib.postgres")

# Obfuscated Admin URL configuration
ADMIN_URL = env("ADMIN_URL", default="admin/")

# Production Security and Hardening Block
if ENVIRONMENT == "production":
    # HTTPS Security
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SOCIAL_AUTH_REDIRECT_IS_HTTPS = True  # Google redirect_uri must be https://

    # Cookie Security
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    # Must stay False: the frontend reads csrftoken from document.cookie for fetch() POSTs.
    CSRF_COOKIE_HTTPONLY = False
    CSRF_TRUSTED_ORIGINS = env.list(
        "CSRF_TRUSTED_ORIGINS", default=[f"https://{h.lstrip('.')}" for h in ALLOWED_HOSTS if h and h != "*"]
    )
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"

    # Content Security
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"  # Razorpay checkout popup
    X_FRAME_OPTIONS = "DENY"

    # Session Expiry
    SESSION_COOKIE_AGE = 86400  # 24 hours
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True

    # Logging
    ADMINS = [("MixMint Admin", env("ADMIN_EMAIL", default="admin@mixmint.site"))]

# Content Security Policy — applies in every environment (the CSP middleware is always on,
# and django-csp's default of default-src 'self' would otherwise block the inline scripts).
# Templates use inline <script> blocks and Alpine.js (which evaluates expressions), so
# 'unsafe-inline'/'unsafe-eval' are required for script-src; every other source is allowlisted.
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",
    "'unsafe-eval'",
    "https://checkout.razorpay.com",
    "https://cdn.jsdelivr.net",
    "https://unpkg.com",
)
CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",
    "https://fonts.googleapis.com",
    "https://api.fontshare.com",
    "https://cdn.jsdelivr.net",
    "https://unpkg.com",
)
CSP_FONT_SRC = (
    "'self'",
    "data:",
    "https://fonts.gstatic.com",
    "https://cdn.fontshare.com",
    "https://api.fontshare.com",
    "https://cdn.jsdelivr.net",
)
CSP_IMG_SRC = ("'self'", "data:", "https:", "blob:")
CSP_MEDIA_SRC = ("'self'", "https:", "blob:")
CSP_CONNECT_SRC = (
    "'self'",
    "https://api.razorpay.com",
    "https://lumberjack.razorpay.com",
    "https://api.phonepe.com",
    "https://api-preprod.phonepe.com",
    "https://*.r2.cloudflarestorage.com",  # DJ uploads go straight to R2 (signed PUT)
    "https://api.fontshare.com",
    "https://fonts.googleapis.com",
)


def _origin(url):
    from urllib.parse import urlsplit

    parts = urlsplit(url or "")
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else ""


for _o in {_origin(AWS_S3_ENDPOINT_URL)} - {""}:
    CSP_CONNECT_SRC += (_o,)
for _o in {_origin(R2_PUBLIC_URL)} - {""}:
    CSP_IMG_SRC += (_o,)
CSP_FRAME_SRC = (
    "'self'",
    "https://www.youtube.com",
    "https://www.youtube-nocookie.com",
    "https://www.instagram.com",
    "https://api.razorpay.com",
    "https://checkout.razorpay.com",
    "https://api.phonepe.com",
    "https://api-preprod.phonepe.com",
)
CSP_BASE_URI = ("'self'",)
CSP_FORM_ACTION = (
    "'self'",
    "https://accounts.google.com",
    "https://api.phonepe.com",
    "https://api-preprod.phonepe.com",
)
CSP_FRAME_ANCESTORS = ("'none'",)
CSP_OBJECT_SRC = ("'none'",)
if ENVIRONMENT == "production":
    CSP_REPORT_URI = "/csp-report/"
