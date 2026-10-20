"""Cashfree Payment Gateway: order creation, popup payload, phone prompt, status check, webhook, refund."""

import base64
import hashlib
import hmac
import json
import time
from decimal import Decimal
from unittest import mock

import pytest
from django.test import Client

from apps.admin_panel.models import SystemSetting
from apps.commerce.models import Purchase


class R:
    def __init__(self, code, body):
        self.status_code, self._b, self.text = code, body, json.dumps(body)

    def json(self):
        return self._b


@pytest.fixture
def cf(settings, db):
    settings.CASHFREE_PG_APP_ID, settings.CASHFREE_PG_SECRET, settings.CASHFREE_PG_ENV = "app_test", "sec_test", "sandbox"
    SystemSetting.objects.update_or_create(key="active_payment_gateway", defaults={"value": {"gateway": "cashfree"}})


@pytest.fixture
def buyer(user):
    c = Client()
    c.force_login(user)
    return c


def cf_calls(m, path):
    return [c for c in m.call_args_list if path in str(c.args[1] if len(c.args) > 1 else c.kwargs.get("url", ""))]


@pytest.mark.django_db
class TestCashfreeCheckout:
    def test_asks_for_phone_first(self, cf, buyer, track):
        with mock.patch("requests.request") as req:
            r = buyer.post("/api/v1/payments/initiate/", {"content_type": "track", "content_id": track.id}, content_type="application/json")
        assert r.status_code == 428 and r.json()["need_phone"] is True
        assert not cf_calls(req, "/orders")
        assert buyer.post("/api/v1/payments/phone/", {"phone": "12345"}, content_type="application/json").status_code == 400
        assert buyer.post("/api/v1/payments/phone/", {"phone": "+91 98765 43210"}, content_type="application/json").status_code == 200

    def test_creates_popup_order(self, cf, buyer, user, track):
        user.profile.phone = "9876543210"
        user.profile.save()
        ok = R(200, {"cf_order_id": "123", "payment_session_id": "session_abc", "order_status": "ACTIVE"})
        with mock.patch("requests.request", return_value=ok) as req:
            r = buyer.post("/api/v1/payments/initiate/", {"content_type": "track", "content_id": track.id}, content_type="application/json")
        assert r.status_code == 200, r.content
        d = r.json()
        assert d["checkout"] == "cashfree" and d["payment_session_id"] == "session_abc" and d["mode"] == "sandbox"
        call = cf_calls(req, "/orders")[-1]
        assert call.args[0] == "POST" and call.args[1] == "https://sandbox.cashfree.com/pg/orders"
        body = call.kwargs["json"]
        assert body["order_id"] == d["order_id"] and body["customer_details"]["customer_phone"] == "9876543210"
        assert body["order_amount"] == float(track.price)
        assert body["order_meta"]["payment_methods"] == "upi,nb"  # no cards
        assert call.kwargs["headers"]["x-client-id"] == "app_test"
        assert Purchase.objects.get(gateway_order_id=d["order_id"]).payment_gateway == "cashfree"

    def test_return_page_confirms_paid_order(self, cf, buyer, user, track):
        user.profile.phone = "9876543210"
        user.profile.save()
        with mock.patch("requests.request", return_value=R(200, {"payment_session_id": "s"})):
            oid = buyer.post("/api/v1/payments/initiate/", {"content_type": "track", "content_id": track.id},
                             content_type="application/json").json()["order_id"]
        amount = str(Purchase.objects.get(gateway_order_id=oid).price_paid)

        def fake(method, url, **kw):
            if url.endswith("/payments"):
                return R(200, [{"cf_payment_id": 555, "payment_status": "SUCCESS", "payment_amount": amount}])
            return R(200, {"order_status": "PAID", "order_amount": amount, "cf_order_id": "1"})

        with mock.patch("requests.request", side_effect=fake):
            r = buyer.get(f"/api/v1/payments/callback/?order_id={oid}")
        assert "payment=success" in r["Location"]
        assert Purchase.objects.get(gateway_order_id=oid).status == "paid"

    def test_webhook_signature_and_fulfil(self, cf, buyer, user, track):
        user.profile.phone = "9876543210"
        user.profile.save()
        with mock.patch("requests.request", return_value=R(200, {"payment_session_id": "s"})):
            oid = buyer.post("/api/v1/payments/initiate/", {"content_type": "track", "content_id": track.id},
                             content_type="application/json").json()["order_id"]
        amount = str(Purchase.objects.get(gateway_order_id=oid).price_paid)
        raw = json.dumps({"type": "PAYMENT_SUCCESS_WEBHOOK", "data": {"order": {"order_id": oid},
                                                                      "payment": {"payment_status": "SUCCESS"}}})
        ts = str(int(time.time()))
        bad = Client().post("/payment/webhook/cashfree/", raw, content_type="application/json",
                            HTTP_X_WEBHOOK_SIGNATURE="nope", HTTP_X_WEBHOOK_TIMESTAMP=ts)
        assert bad.status_code == 401
        sig = base64.b64encode(hmac.new(b"sec_test", (ts + raw).encode(), hashlib.sha256).digest()).decode()

        def fake(method, url, **kw):
            if url.endswith("/payments"):
                return R(200, [{"cf_payment_id": 9, "payment_status": "SUCCESS", "payment_amount": amount}])
            return R(200, {"order_status": "PAID", "order_amount": amount})

        with mock.patch("requests.request", side_effect=fake):
            ok = Client().post("/payment/webhook/cashfree/", raw, content_type="application/json",
                               HTTP_X_WEBHOOK_SIGNATURE=sig, HTTP_X_WEBHOOK_TIMESTAMP=ts)
        assert ok.status_code == 200
        assert Purchase.objects.get(gateway_order_id=oid).status == "paid"

    def test_dropped_payment_fails_order(self, cf, buyer, user, track):
        user.profile.phone = "9876543210"
        user.profile.save()
        with mock.patch("requests.request", return_value=R(200, {"payment_session_id": "s"})):
            oid = buyer.post("/api/v1/payments/initiate/", {"content_type": "track", "content_id": track.id},
                             content_type="application/json").json()["order_id"]
        raw = json.dumps({"type": "PAYMENT_USER_DROPPED_WEBHOOK", "data": {"order": {"order_id": oid}}})
        ts = "1700000000"
        sig = base64.b64encode(hmac.new(b"sec_test", (ts + raw).encode(), hashlib.sha256).digest()).decode()
        with mock.patch("requests.request", return_value=R(200, {"order_status": "ACTIVE", "order_amount": "1"})):
            Client().post("/payment/webhook/cashfree/", raw, content_type="application/json",
                          HTTP_X_WEBHOOK_SIGNATURE=sig, HTTP_X_WEBHOOK_TIMESTAMP=ts)
        assert Purchase.objects.get(gateway_order_id=oid).status == "failed"

    def test_refund(self, cf):
        from apps.payments.cashfree_pg import CashfreeGateway

        with mock.patch("requests.request", return_value=R(200, {"cf_refund_id": "77", "refund_status": "PENDING"})) as req:
            out = CashfreeGateway().process_refund("MM_X", 10500, "Buyer asked")
        assert out["success"] and req.call_args.kwargs["json"]["refund_amount"] == 105.0
        assert req.call_args.args[1].endswith("/pg/orders/MM_X/refunds")

    def test_label_and_test_banner(self, cf, client):
        from django.core.cache import cache

        cache.clear()
        body = client.get("/").content.decode()
        assert "TEST MODE" in body or "test" in body.lower()


def test_clean_phone():
    from apps.payments.cashfree_pg import clean_phone

    assert clean_phone("+91 98765-43210") == "9876543210"
    assert clean_phone("09876543210") == "9876543210"
    assert clean_phone("5876543210") == "" and clean_phone("98765") == ""
