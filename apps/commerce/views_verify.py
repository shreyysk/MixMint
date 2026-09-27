"""
Legacy purchase-verification endpoint.

It used to create *paid* purchases from client-supplied data (and skipped
verification entirely for PhonePe). It now only accepts a signed Razorpay
checkout result for an order this user already created via /payments/initiate/,
and fulfils it through the same path as every other payment.
"""

import json

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from apps.payments.views import razorpay_confirm


@login_required
@require_POST
def verify_purchase_view(request):
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = {}
    # Map the legacy field names onto the confirm endpoint's.
    request._body = json.dumps(
        {
            "razorpay_order_id": data.get("orderId") or data.get("order_id"),
            "razorpay_payment_id": data.get("paymentId") or data.get("payment_id"),
            "razorpay_signature": data.get("signature"),
        }
    ).encode()
    return razorpay_confirm(request)
