"""
PhonePe Payment Gateway — Standard Checkout v2 (the API PhonePe gives new merchants).

    1. POST /v1/oauth/token        client_id + client_secret + client_version → O-Bearer token (cached)
    2. POST /checkout/v2/pay       merchantOrderId + amount → redirectUrl of PhonePe's payment page
    3. buyer pays on PhonePe → comes back to /api/v1/payments/callback/?order_id=…
       → GET /checkout/v2/order/{merchantOrderId}/status is the source of truth
    4. PhonePe also calls /api/v1/payments/webhook/phonepe/ (Authorization: SHA256(user:password))
    5. Refunds: POST /payments/v2/refund

Settings (Vercel env):
    PHONEPE_CLIENT_ID, PHONEPE_CLIENT_SECRET, PHONEPE_CLIENT_VERSION   from the PhonePe Business dashboard
    PHONEPE_ENV = "sandbox" (UAT test credentials) or "production" (live credentials)
    PHONEPE_WEBHOOK_USERNAME, PHONEPE_WEBHOOK_PASSWORD                 the ones you set on the webhook

Older merchants on the salt-key API (PHONEPE_MERCHANT_ID + PHONEPE_SALT_KEY, no client id) still
work through the legacy v1 code path at the bottom of this file.
"""

import base64
import hashlib
import hmac
import json
import logging
import time
import uuid

import requests
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

from .base import PaymentGateway

logger = logging.getLogger("mixmint")

HOSTS = {
    "sandbox": {
        "auth": "https://api-preprod.phonepe.com/apis/pg-sandbox/v1/oauth/token",
        "pg": "https://api-preprod.phonepe.com/apis/pg-sandbox",
    },
    "production": {
        "auth": "https://api.phonepe.com/apis/identity-manager/v1/oauth/token",
        "pg": "https://api.phonepe.com/apis/pg",
    },
}
# v2 order state → the status words the rest of MixMint already understands
STATE_MAP = {"COMPLETED": "PAYMENT_SUCCESS", "FAILED": "PAYMENT_DECLINED", "PENDING": "PAYMENT_PENDING"}


def phonepe_env():
    env = (getattr(settings, "PHONEPE_ENV", "") or "sandbox").lower()
    return env if env in HOSTS else "sandbox"


def is_v2_configured():
    return bool(getattr(settings, "PHONEPE_CLIENT_ID", "") and getattr(settings, "PHONEPE_CLIENT_SECRET", ""))


class PhonePeError(Exception):
    pass


class PhonePeGateway(PaymentGateway):
    name = "phonepe"

    def __init__(self):
        self.v2 = is_v2_configured()
        if self.v2:
            self.client_id = settings.PHONEPE_CLIENT_ID
            self.client_secret = settings.PHONEPE_CLIENT_SECRET
            self.client_version = str(getattr(settings, "PHONEPE_CLIENT_VERSION", "") or "1")
            self.env = phonepe_env()
            self.pg = HOSTS[self.env]["pg"]
            return
        # legacy salt-key merchants
        self.merchant_id = getattr(settings, "PHONEPE_MERCHANT_ID", "")
        self.salt_key = getattr(settings, "PHONEPE_SALT_KEY", "")
        self.salt_index = getattr(settings, "PHONEPE_SALT_INDEX", "1")
        if not self.merchant_id or not self.salt_key:
            raise ImproperlyConfigured(
                "PhonePe is not configured. Set PHONEPE_CLIENT_ID, PHONEPE_CLIENT_SECRET and PHONEPE_CLIENT_VERSION."
            )
        self.base_url = getattr(settings, "PHONEPE_BASE_URL", "https://api-preprod.phonepe.com/apis/pg-sandbox")

    # ─────────────────────────────── v2 plumbing ───────────────────────────────
    def _token(self, force=False):
        key = f"phonepe_token:{self.env}:{self.client_id}"
        if not force:
            cached = cache.get(key)
            if cached:
                return cached
        r = requests.post(
            HOSTS[self.env]["auth"],
            data={"client_id": self.client_id, "client_version": self.client_version,
                  "client_secret": self.client_secret, "grant_type": "client_credentials"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20,
        )
        try:
            data = r.json()
        except ValueError:
            data = {}
        token = data.get("access_token")
        if r.status_code >= 400 or not token:
            raise PhonePeError(f"PhonePe login failed ({r.status_code}): {data.get('message') or data.get('code') or 'check client id/secret/version and PHONEPE_ENV'}")
        ttl = int(data.get("expires_at") or 0) - int(time.time()) - 120
        cache.set(key, token, timeout=max(60, min(ttl, 3600)) if ttl > 0 else 600)
        return token

    def _call(self, method, path, body=None):
        for attempt in (0, 1):
            headers = {"Content-Type": "application/json", "Authorization": f"O-Bearer {self._token(force=bool(attempt))}"}
            r = requests.request(method, f"{self.pg}{path}", json=body, headers=headers, timeout=30)
            if r.status_code == 401 and attempt == 0:
                continue  # token expired early: get a fresh one and retry once
            try:
                data = r.json()
            except ValueError:
                data = {"message": r.text[:200]}
            return r.status_code, data
        return r.status_code, data

    # ─────────────────────────────── gateway interface ───────────────────────────────
    def create_order(self, amount_paise, currency="INR", order_id=None, metadata=None):
        if not self.v2:
            return self._v1_create_order(amount_paise, order_id, metadata)
        order_id = order_id or f"MM_{uuid.uuid4().hex[:16].upper()}"
        metadata = metadata or {}
        base = (settings.BASE_URL or "").rstrip("/")
        body = {
            "merchantOrderId": order_id,
            "amount": int(amount_paise),
            "expireAfter": 1200,  # 20 minutes, a little longer than our 15-minute copy hold
            "metaInfo": {"udf1": str(metadata.get("user_id", ""))[:256], "udf2": str(metadata.get("purpose", "purchase"))[:256]},
            "paymentFlow": {
                "type": "PG_CHECKOUT",
                "message": str(metadata.get("description", "MixMint purchase"))[:100],
                "merchantUrls": {"redirectUrl": f"{base}/api/v1/payments/callback/?order_id={order_id}"},
            },
        }
        code, data = self._call("POST", "/checkout/v2/pay", body)
        if code >= 400 or not data.get("redirectUrl"):
            raise PhonePeError(f"PhonePe order creation failed: {data.get('message') or data.get('code') or code}")
        return {
            "success": True,
            "checkout": "redirect",
            "order_id": order_id,
            "gateway_order_id": order_id,  # we always look orders up by our own merchantOrderId
            "phonepe_order_id": data.get("orderId"),
            "redirect_url": data["redirectUrl"],
            "gateway_response": data,
        }

    def get_payment_status(self, merchant_order_id):
        if not self.v2:
            return self._v1_status(merchant_order_id)
        code, data = self._call("GET", f"/checkout/v2/order/{merchant_order_id}/status?details=false")
        state = data.get("state", "")
        attempts = data.get("paymentDetails") or []
        txn = (attempts[-1] if attempts else {}).get("transactionId", "")
        return {
            "success": code < 400 and bool(state),
            "status": STATE_MAP.get(state, "PAYMENT_PENDING" if code < 400 else ""),
            "amount": data.get("amount", 0),
            "transaction_id": txn,
            "gateway_response": data,
        }

    def process_refund(self, original_order_id, amount_paise, reason=""):
        if not self.v2:
            return self._v1_refund(original_order_id, amount_paise)
        refund_id = f"RF_{uuid.uuid4().hex[:20].upper()}"
        code, data = self._call("POST", "/payments/v2/refund", {
            "merchantRefundId": refund_id, "originalMerchantOrderId": original_order_id, "amount": int(amount_paise),
        })
        if code >= 400 or data.get("state") == "FAILED":
            raise PhonePeError(f"PhonePe refund failed: {data.get('message') or data.get('code') or code}")
        return {"success": True, "refund_id": data.get("refundId") or refund_id, "merchant_refund_id": refund_id,
                "state": data.get("state"), "gateway_response": data}

    def verify_payment(self, payload, signature):
        """Webhook check. v2: Authorization header == sha256("username:password")."""
        if not self.v2:
            return self._v1_verify(payload, signature)
        user = getattr(settings, "PHONEPE_WEBHOOK_USERNAME", "") or ""
        pwd = getattr(settings, "PHONEPE_WEBHOOK_PASSWORD", "") or ""
        if not (user and pwd and signature):
            return False
        expected = hashlib.sha256(f"{user}:{pwd}".encode()).hexdigest()
        given = signature.strip()
        for prefix in ("SHA256 ", "sha256 ", "SHA256=", "Bearer "):
            if given.startswith(prefix):
                given = given[len(prefix):].strip()
        return hmac.compare_digest(expected.lower(), given.lower())

    def create_subscription_order(self, dj_id, plan_type, amount_paise):
        from django.utils import timezone

        order_id = f"PRO_{str(dj_id)[:8].upper()}_{timezone.now().strftime('%Y%m%d%H%M%S')}"
        return self.create_order(amount_paise=amount_paise, order_id=order_id,
                                 metadata={"user_id": str(dj_id), "purpose": "pro_subscription", "plan_type": plan_type})

    def create_overage_order(self, dj_id, overage_gb, amount_paise):
        from django.utils import timezone

        order_id = f"OVERAGE_{str(dj_id)[:8].upper()}_{timezone.now().strftime('%Y%m%d%H%M%S')}"
        return self.create_order(amount_paise=amount_paise, order_id=order_id,
                                 metadata={"user_id": str(dj_id), "purpose": "storage_overage", "overage_gb": overage_gb})

    # ─────────────────────────────── legacy v1 (salt key) ───────────────────────────────
    def _checksum(self, payload_base64, endpoint):
        return hashlib.sha256((payload_base64 + endpoint + self.salt_key).encode()).hexdigest() + "###" + self.salt_index

    def _v1_create_order(self, amount_paise, order_id, metadata):
        order_id = order_id or f"MM_{uuid.uuid4().hex[:16].upper()}"
        metadata = metadata or {}
        payload = {
            "merchantId": self.merchant_id, "merchantTransactionId": order_id,
            "merchantUserId": metadata.get("user_id", "unknown"), "amount": int(amount_paise),
            "redirectUrl": f"{settings.BASE_URL}/api/v1/payments/callback/?order_id={order_id}", "redirectMode": "REDIRECT",
            "callbackUrl": f"{settings.BASE_URL}/api/v1/payments/webhook/phonepe/", "paymentInstrument": {"type": "PAY_PAGE"},
        }
        b64 = base64.b64encode(json.dumps(payload).encode()).decode()
        r = requests.post(f"{self.base_url}/pg/v1/pay", json={"request": b64}, timeout=30, headers={
            "Content-Type": "application/json", "X-VERIFY": self._checksum(b64, "/pg/v1/pay"), "X-MERCHANT-ID": self.merchant_id})
        data = r.json()
        if data.get("success") and data.get("data", {}).get("instrumentResponse"):
            return {"success": True, "checkout": "redirect", "order_id": order_id, "gateway_order_id": order_id,
                    "redirect_url": data["data"]["instrumentResponse"]["redirectInfo"]["url"], "gateway_response": data}
        raise PhonePeError(f"PhonePe order creation failed: {data.get('message', 'Unknown error')}")

    def _v1_status(self, merchant_transaction_id):
        endpoint = f"/pg/v1/status/{self.merchant_id}/{merchant_transaction_id}"
        r = requests.get(f"{self.base_url}{endpoint}", timeout=30, headers={
            "Content-Type": "application/json", "X-VERIFY": self._checksum("", endpoint),
            "X-MERCHANT-ID": self.merchant_id, "X-VERIFY-INDEX": self.salt_index})
        data = r.json()
        return {"success": data.get("success", False), "status": data.get("code", ""),
                "amount": data.get("data", {}).get("amount", 0),
                "transaction_id": data.get("data", {}).get("transactionId", ""), "gateway_response": data}

    def _v1_refund(self, original_transaction_id, amount_paise):
        refund_id = f"REFUND_{uuid.uuid4().hex[:16].upper()}"
        payload = {"merchantId": self.merchant_id, "merchantUserId": "INTERNAL", "originalTransactionId": original_transaction_id,
                   "merchantTransactionId": refund_id, "amount": int(amount_paise),
                   "callbackUrl": f"{settings.BASE_URL}/api/v1/payments/webhook/phonepe/"}
        b64 = base64.b64encode(json.dumps(payload).encode()).decode()
        r = requests.post(f"{self.base_url}/pg/v1/refund", json={"request": b64}, timeout=30, headers={
            "Content-Type": "application/json", "X-VERIFY": self._checksum(b64, "/pg/v1/refund"), "X-MERCHANT-ID": self.merchant_id})
        data = r.json()
        if data.get("success"):
            return {"success": True, "refund_id": refund_id, "gateway_response": data}
        raise PhonePeError(f"PhonePe refund failed: {data.get('message', 'Unknown error')}")

    def _v1_verify(self, payload_base64, x_verify_header):
        if not x_verify_header:
            return False
        expected = hashlib.sha256((payload_base64 + self.salt_key).encode()).hexdigest() + "###" + self.salt_index
        return hmac.compare_digest(expected, x_verify_header)
