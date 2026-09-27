import hashlib
import hmac
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .base import PaymentGateway

logger = logging.getLogger("mixmint")


class RazorpayGateway(PaymentGateway):
    """
    Razorpay integration (Standard Checkout).

    Razorpay has no hosted redirect page: the browser opens checkout.js with the
    `order_id` we return, then posts the signed result to
    /api/v1/payments/razorpay/confirm/. Webhooks are the server-side backstop.
    """

    name = "razorpay"

    def __init__(self):
        self.key_id = getattr(settings, "RAZORPAY_KEY_ID", "")
        self.key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
        if not self.key_id or not self.key_secret:
            raise ImproperlyConfigured("Razorpay credentials not configured (RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET).")
        import razorpay  # lazy: only needed when a Razorpay call is made

        self.client = razorpay.Client(auth=(self.key_id, self.key_secret))

    def create_order(self, amount_paise, currency="INR", order_id=None, metadata=None):
        notes = {k: str(v) for k, v in (metadata or {}).items() if not isinstance(v, (list, dict))}
        data = {"amount": int(amount_paise), "currency": currency, "receipt": (order_id or "")[:40], "notes": notes}
        order = self.client.order.create(data=data)
        return {
            "success": True,
            "checkout": "razorpay",
            # The Razorpay order id is what webhooks and checkout.js reference,
            # so it is the id we persist as Purchase.gateway_order_id.
            "order_id": order["id"],
            "gateway_order_id": order["id"],
            "amount": order["amount"],
            "currency": currency,
            "key": self.key_id,
            "gateway_response": order,
        }

    # -- verification -----------------------------------------------------
    def verify_payment(self, payload, signature):
        """Verify a checkout.js success handler signature. payload = {order_id, payment_id}."""
        if not isinstance(payload, dict) or not signature:
            return False
        try:
            self.client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": payload.get("order_id"),
                    "razorpay_payment_id": payload.get("payment_id"),
                    "razorpay_signature": signature,
                }
            )
            return True
        except Exception:
            return False

    @staticmethod
    def verify_webhook(raw_body: bytes, signature: str) -> bool:
        """Webhooks are signed with the *webhook secret* set in the Razorpay dashboard."""
        secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "") or ""
        if not secret:
            logger.error("RAZORPAY_WEBHOOK_SECRET is not set; rejecting Razorpay webhook.")
            return False
        if not signature:
            return False
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    # -- status / refunds ---------------------------------------------------
    def get_payment_status(self, order_id):
        """Status for a Razorpay *order* id (order_xxx)."""
        payments = self.client.order.payments(order_id).get("items", [])
        captured = next((p for p in payments if p.get("status") == "captured"), None)
        if captured:
            return {
                "success": True,
                "status": "PAYMENT_SUCCESS",
                "amount": captured["amount"],
                "transaction_id": captured["id"],
                "gateway_response": captured,
            }
        failed = payments and all(p.get("status") == "failed" for p in payments)
        return {
            "success": False,
            "status": "PAYMENT_DECLINED" if failed else "PAYMENT_PENDING",
            "amount": 0,
            "transaction_id": "",
            "gateway_response": {"items": payments},
        }

    def fetch_payment(self, payment_id):
        return self.client.payment.fetch(payment_id)

    def process_refund(self, transaction_id, amount_paise, reason=""):
        refund = self.client.payment.refund(transaction_id, {"amount": int(amount_paise), "notes": {"reason": reason}})
        return {"success": True, "refund_id": refund["id"], "gateway_response": refund}

    def create_subscription_order(self, dj_id, plan_type, amount_paise):
        return self.create_order(
            amount_paise, order_id=f"PRO_{dj_id}", metadata={"dj_id": str(dj_id), "purpose": "pro_subscription"}
        )

    def create_overage_order(self, dj_id, overage_gb, amount_paise):
        return self.create_order(
            amount_paise, order_id=f"OVERAGE_{dj_id}", metadata={"dj_id": str(dj_id), "purpose": "storage_overage"}
        )
