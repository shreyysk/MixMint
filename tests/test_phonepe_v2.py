"""PhonePe Standard Checkout v2: login token, pay page, status as source of truth, webhook, refund."""

import hashlib
import json
import time
from decimal import Decimal
from unittest import mock

import pytest
from django.core.cache import cache
from django.test import Client

V2 = dict(PHONEPE_CLIENT_ID="TESTCLIENT", PHONEPE_CLIENT_SECRET="secret", PHONEPE_CLIENT_VERSION="1",
          PHONEPE_ENV="sandbox", PHONEPE_WEBHOOK_USERNAME="mmhook", PHONEPE_WEBHOOK_PASSWORD="hookpass",
          DEFAULT_PAYMENT_GATEWAY="phonepe", BASE_URL="https://mixmint.site")


class FakePhonePe:
    def __init__(self):
        self.calls, self.orders, self.tokens = [], {}, 0

    def post(self, url, data=None, headers=None, timeout=None):  # oauth
        assert url.endswith("/v1/oauth/token") and data["grant_type"] == "client_credentials"
        self.tokens += 1
        return mock.Mock(status_code=200, json=lambda: {"access_token": f"TOK{self.tokens}", "token_type": "O-Bearer",
                                                       "expires_at": int(time.time()) + 3600})

    def request(self, method, url, json=None, headers=None, timeout=None):
        assert headers["Authorization"].startswith("O-Bearer TOK")
        self.calls.append((method, url, json))
        if url.endswith("/checkout/v2/pay"):
            self.orders[json["merchantOrderId"]] = {"amount": json["amount"], "state": "PENDING"}
            body = {"orderId": "OMO1", "state": "PENDING", "redirectUrl": "https://mercury-uat.phonepe.com/transact/x"}
        elif "/checkout/v2/order/" in url:
            oid = url.split("/checkout/v2/order/")[1].split("/")[0]
            o = self.orders[oid]
            body = {"orderId": "OMO1", "state": o["state"], "amount": o["amount"],
                    "paymentDetails": [{"transactionId": "TXN9", "state": o["state"]}]}
        elif url.endswith("/payments/v2/refund"):
            body = {"refundId": "OMR1", "amount": json["amount"], "state": "PENDING"}
        else:
            raise AssertionError(url)
        return mock.Mock(status_code=200, json=lambda: body)


@pytest.fixture
def phonepe(settings):
    for k, v in V2.items():
        setattr(settings, k, v)
    cache.clear()
    fake = FakePhonePe()
    with mock.patch("apps.payments.phonepe.requests", fake):
        yield fake


def _buy(user, track):
    c = Client()
    c.force_login(user)
    return c, c.post("/api/v1/payments/initiate/", json.dumps({"content_id": track.id, "content_type": "track"}),
                     content_type="application/json")


@pytest.mark.django_db
def test_pay_page_then_callback_marks_paid(phonepe, user, track):
    from apps.commerce.models import Purchase

    c, r = _buy(user, track)
    assert r.status_code == 200, r.content
    data = r.json()
    assert data["checkout"] == "redirect" and data["redirect_url"].startswith("https://mercury-uat.phonepe.com")
    method, url, body = phonepe.calls[0]
    assert url == "https://api-preprod.phonepe.com/apis/pg-sandbox/checkout/v2/pay"
    assert body["paymentFlow"]["type"] == "PG_CHECKOUT"
    assert body["paymentFlow"]["merchantUrls"]["redirectUrl"].endswith(f"/api/v1/payments/callback/?order_id={data['order_id']}")
    p = Purchase.objects.get(gateway_order_id=data["order_id"])
    assert p.status == "pending" and p.payment_gateway == "phonepe"

    # Coming back before paying: still pending.
    assert "payment=pending" in c.get(f"/api/v1/payments/callback/?order_id={data['order_id']}")["Location"]
    phonepe.orders[data["order_id"]]["state"] = "COMPLETED"
    assert "payment=success" in c.get(f"/api/v1/payments/callback/?order_id={data['order_id']}")["Location"]
    p.refresh_from_db()
    assert p.status == "paid"
    assert phonepe.tokens == 1  # token reused from cache


@pytest.mark.django_db
def test_failed_payment(phonepe, user, track):
    from apps.commerce.models import Purchase

    c, r = _buy(user, track)
    oid = r.json()["order_id"]
    phonepe.orders[oid]["state"] = "FAILED"
    assert "payment=failed" in c.get(f"/api/v1/payments/callback/?order_id={oid}")["Location"]
    assert Purchase.objects.get(gateway_order_id=oid).status == "failed"


@pytest.mark.django_db
def test_webhook_needs_auth_and_uses_status_api(phonepe, user, track):
    from apps.commerce.models import Purchase

    c, r = _buy(user, track)
    oid = r.json()["order_id"]
    hook = {"event": "checkout.order.completed", "payload": {"merchantOrderId": oid, "state": "COMPLETED", "amount": 1}}
    anon = Client()
    assert anon.post("/api/v1/payments/webhook/phonepe/", json.dumps(hook), content_type="application/json",
                     HTTP_AUTHORIZATION="nope").status_code == 401
    good = hashlib.sha256(b"mmhook:hookpass").hexdigest()
    # A forged "completed" webhook can't mark it paid: the status API still says PENDING.
    assert anon.post("/api/v1/payments/webhook/phonepe/", json.dumps(hook), content_type="application/json",
                     HTTP_AUTHORIZATION=good).status_code == 200
    assert Purchase.objects.get(gateway_order_id=oid).status == "pending"
    phonepe.orders[oid]["state"] = "COMPLETED"
    assert anon.post("/api/v1/payments/webhook/phonepe/", json.dumps(hook), content_type="application/json",
                     HTTP_AUTHORIZATION=good).status_code == 200
    assert Purchase.objects.get(gateway_order_id=oid).status == "paid"


@pytest.mark.django_db
def test_refund_uses_v2(phonepe):
    from apps.payments.phonepe import PhonePeGateway

    res = PhonePeGateway().process_refund("MM_ABC", 9900)
    method, url, body = phonepe.calls[-1]
    assert url.endswith("/payments/v2/refund") and body["originalMerchantOrderId"] == "MM_ABC" and body["amount"] == 9900
    assert res["refund_id"] == "OMR1" and body["merchantRefundId"].startswith("RF_") and len(body["merchantRefundId"]) <= 63


@pytest.mark.django_db
def test_production_hosts(phonepe, settings):
    from apps.payments.phonepe import PhonePeGateway

    settings.PHONEPE_ENV = "production"
    gw = PhonePeGateway()
    assert gw.pg == "https://api.phonepe.com/apis/pg"


@pytest.mark.django_db
def test_banner_and_admin_card(phonepe, client, admin_user, settings):
    cache.clear()
    assert b"TEST MODE" in client.get("/").content  # sandbox keys → banner
    settings.PHONEPE_ENV = "production"
    cache.clear()
    assert b"TEST MODE" not in client.get("/").content
    a = Client()
    a.force_login(admin_user)
    with mock.patch("apps.admin_panel.support.webhook_info", return_value={}):
        html = a.get("/api/v1/admin/support/").content.decode()
        assert "New orders go through <b" in html and "PhonePe" in html and "/api/v1/payments/webhook/phonepe/" in html
        r = a.post("/api/v1/admin/support/", {"action": "gateway_test"}, follow=True)
        assert "PhonePe connection OK" in r.content.decode()
        a.post("/api/v1/admin/support/", {"action": "gateway_switch", "gateway": "razorpay"})
    from apps.payments.utils import active_gateway_name

    assert active_gateway_name() == "razorpay"
