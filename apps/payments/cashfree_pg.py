"""Cashfree Payment Gateway (collect payments). Checkout opens as a popup on MixMint (JS SDK v3, "_modal").

Flow:
  1. create_order -> POST /pg/orders -> payment_session_id
  2. browser: Cashfree({mode}).checkout({paymentSessionId, redirectTarget: "_modal"})
  3. when the popup finishes, the browser goes to /api/v1/payments/callback/?order_id=... and MixMint asks
     Cashfree for the order's real status (GET /pg/orders/{id}); the webhook is the server-side backstop.

Env: CASHFREE_PG_APP_ID, CASHFREE_PG_SECRET, CASHFREE_PG_ENV ("sandbox" | "production").
Cashfree needs the buyer's mobile number on every order; if MixMint doesn't have it yet, NeedPhone is raised
and the browser asks for it once (saved on the profile).
"""

import base64
import hashlib
import hmac
import logging
import re
import uuid
from decimal import ROUND_HALF_UP, Decimal

import requests
from django.conf import settings

from .base import PaymentGateway

logger = logging.getLogger("mixmint")
API_VERSION = "2025-01-01"
TIMEOUT = 15
PHONE_RE = re.compile(r"^[6-9]\d{9}$")


class CashfreeError(Exception):
    pass


class NeedPhone(Exception):
    """The buyer's mobile number is needed before Cashfree can create the order."""


def clean_phone(raw):
    digits = re.sub(r"\D", "", str(raw or ""))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits if PHONE_RE.match(digits) else ""


def cashfree_env():
    return "production" if (getattr(settings, "CASHFREE_PG_ENV", "sandbox") or "").lower() == "production" else "sandbox"


def is_configured():
    return bool(getattr(settings, "CASHFREE_PG_APP_ID", "") and getattr(settings, "CASHFREE_PG_SECRET", ""))


def _profile_for(user_id):
    from apps.accounts.models import DJProfile, Profile

    uid = str(user_id or "")
    if not uid:
        return None
    try:
        p = Profile.objects.select_related("user").filter(pk=uid).first()
    except Exception:
        p = None
    if p is None:
        try:
            dj = DJProfile.objects.select_related("profile__user").filter(pk=uid).first()
            p = dj.profile if dj else None
        except Exception:
            p = None
    return p


class CashfreeGateway(PaymentGateway):
    name = "cashfree"

    def __init__(self):
        if not is_configured():
            raise CashfreeError("Cashfree keys are not set (CASHFREE_PG_APP_ID / CASHFREE_PG_SECRET).")
        self.app_id = settings.CASHFREE_PG_APP_ID
        self.secret = settings.CASHFREE_PG_SECRET
        self.env = cashfree_env()
        self.base = "https://api.cashfree.com/pg" if self.env == "production" else "https://sandbox.cashfree.com/pg"

    def _headers(self, idempotency=None):
        h = {"x-client-id": self.app_id, "x-client-secret": self.secret, "x-api-version": API_VERSION,
             "Content-Type": "application/json", "Accept": "application/json"}
        if idempotency:
            h["x-idempotency-key"] = idempotency
        return h

    def _call(self, method, path, body=None, idempotency=None):
        try:
            r = requests.request(method, f"{self.base}{path}", json=body, headers=self._headers(idempotency), timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise CashfreeError(f"Cashfree did not answer: {exc}") from exc
        try:
            data = r.json()
        except ValueError:
            data = {"message": (r.text or "")[:200]}
        return r.status_code, data if isinstance(data, dict) else {"items": data}

    # ─────────────────────────────── gateway interface ───────────────────────────────
    def create_order(self, amount_paise, currency="INR", order_id=None, metadata=None):
        metadata = metadata or {}
        order_id = order_id or f"MM_{uuid.uuid4().hex[:16].upper()}"
        profile = _profile_for(metadata.get("user_id"))
        phone = clean_phone(metadata.get("phone") or getattr(profile, "phone", ""))
        if not phone:
            raise NeedPhone("Add your mobile number to pay.")
        email = getattr(getattr(profile, "user", None), "email", "") or ""
        name = (getattr(profile, "full_name", "") or email.split("@")[0] or "MixMint buyer")[:100]
        base = (getattr(settings, "BASE_URL", "") or "https://mixmint.site").rstrip("/")
        amount = (Decimal(int(amount_paise)) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        body = {
            "order_id": order_id,
            "order_amount": float(amount),
            "order_currency": currency or "INR",
            "customer_details": {
                "customer_id": re.sub(r"[^A-Za-z0-9_-]", "", str(getattr(profile, "pk", "") or "guest"))[:50] or "guest",
                "customer_phone": phone,
                "customer_email": email or None,
                "customer_name": name,
            },
            "order_meta": {
                "return_url": f"{base}/api/v1/payments/callback/?order_id={order_id}",
                "notify_url": f"{base}/payment/webhook/cashfree/",
            },
            "order_note": str(metadata.get("description") or metadata.get("purpose") or "MixMint purchase")[:200],
            "order_tags": {"purpose": str(metadata.get("purpose", "purchase"))[:50]},
        }
        body["customer_details"] = {k: v for k, v in body["customer_details"].items() if v}
        code, data = self._call("POST", "/orders", body, idempotency=order_id)
        if code >= 400 or not data.get("payment_session_id"):
            raise CashfreeError(f"Cashfree order failed: {data.get('message') or data.get('code') or code}")
        return {
            "success": True,
            "checkout": "cashfree",
            "order_id": order_id,
            "gateway_order_id": order_id,  # we always look orders up by our own order_id
            "cf_order_id": data.get("cf_order_id"),
            "payment_session_id": data["payment_session_id"],
            "mode": self.env,
            "gateway_response": {k: data.get(k) for k in ("cf_order_id", "order_status", "order_expiry_time")},
        }

    def get_payment_status(self, order_id):
        code, data = self._call("GET", f"/orders/{order_id}")
        if code >= 400:
            return {"success": False, "status": "", "amount": 0, "transaction_id": "", "gateway_response": data}
        st = (data.get("order_status") or "").upper()
        amount_paise = int((Decimal(str(data.get("order_amount") or 0)) * 100).to_integral_value(rounding=ROUND_HALF_UP))
        txn, status = "", "PAYMENT_PENDING"
        if st == "PAID":
            status = "PAYMENT_SUCCESS"
            pc, payments = self._call("GET", f"/orders/{order_id}/payments")
            items = payments.get("items") if isinstance(payments, dict) else None
            ok = [p for p in (items or []) if str(p.get("payment_status", "")).upper() == "SUCCESS"]
            if ok:
                txn = str(ok[-1].get("cf_payment_id") or "")
                amount_paise = int((Decimal(str(ok[-1].get("payment_amount") or data.get("order_amount") or 0)) * 100)
                                   .to_integral_value(rounding=ROUND_HALF_UP))
        elif st in ("EXPIRED", "TERMINATED"):
            status = "TIMED_OUT"
        return {"success": True, "status": status, "amount": amount_paise, "transaction_id": txn,
                "gateway_response": {"order_status": st, "cf_order_id": data.get("cf_order_id")}}

    def process_refund(self, order_id, amount_paise, reason=""):
        refund_id = f"RF_{uuid.uuid4().hex[:20].upper()}"
        amount = (Decimal(int(amount_paise)) / 100).quantize(Decimal("0.01"))
        note = re.sub(r"[^A-Za-z0-9 .,-]", "", reason or "MixMint refund")[:100]
        body = {"refund_id": refund_id, "refund_amount": float(amount), "refund_note": note if len(note) >= 3 else "MixMint refund"}
        code, data = self._call("POST", f"/orders/{order_id}/refunds", body, idempotency=refund_id)
        if code >= 400 or str(data.get("refund_status", "")).upper() in ("FAILED", "CANCELLED"):
            raise CashfreeError(f"Cashfree refund failed: {data.get('message') or data.get('refund_status') or code}")
        return {"success": True, "refund_id": data.get("cf_refund_id") or refund_id, "merchant_refund_id": refund_id,
                "state": data.get("refund_status"), "gateway_response": data}

    def verify_payment(self, payload, signature, timestamp=""):
        """Webhook check: base64(HMAC-SHA256(timestamp + raw body, secret)) == x-webhook-signature."""
        if not (signature and timestamp):
            return False
        raw = payload.decode("utf-8") if isinstance(payload, (bytes, bytearray)) else str(payload)
        mac = base64.b64encode(hmac.new(self.secret.encode(), (timestamp + raw).encode(), hashlib.sha256).digest()).decode()
        return hmac.compare_digest(mac, signature)

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
