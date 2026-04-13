"""
Test settings for MixMint.

These settings are used by the audit regression suite to ensure tests do not
depend on external services (Supabase Postgres, R2, Razorpay, Resend).
"""

import os

# Must set ENVIRONMENT before importing settings to prevent production safety check
os.environ.setdefault('ENVIRONMENT', 'test')

from .settings import *  # noqa: F403, F401

# Deterministic, isolated test environment
DEBUG = True
ENVIRONMENT = 'test'
SECRET_KEY = os.environ.get("SECRET_KEY", "mixmint-test-secret-key")

# Always use in-memory SQLite for tests (no external DB).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Fast password hashing in tests.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Local in-memory email backend to assert emails were sent.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Local in-memory cache for throttles / counters.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "mixmint-test-cache",
    }
}

# Dummy external service configuration.
AWS_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "test")
AWS_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "test")
AWS_STORAGE_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "test-bucket")
AWS_S3_ENDPOINT_URL = os.environ.get("R2_ENDPOINT", "https://example.invalid")
AWS_S3_CUSTOM_DOMAIN = ""

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "rzp_secret_test")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "re_test")

# PhonePe test configuration
PHONEPE_MERCHANT_ID = "PGTESTPAYUAT"
PHONEPE_SALT_KEY = "099eb0cd-02cf-4e2a-8aca-3e6c6aff0399"
PHONEPE_SALT_INDEX = "1"
PHONEPE_BASE_URL = "https://api-preprod.phonepe.com/apis/pg-sandbox"

# Disable WhiteNoise compression for tests to avoid staticfiles issues
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# Disable throttling in tests
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = ()  # noqa: F405
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}  # noqa: F405
