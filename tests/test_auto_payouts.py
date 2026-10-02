"""Automatic DJ payouts: provider sends, approvals, failures return money, webhooks, status sync, safety."""

import base64
import hashlib
import hmac
import json
import time
from decimal import Decimal
from unittest import mock

import pytest
import requests
from django.test import Client

from apps.admin_panel.models import SystemSetting
from apps.commerce import payout_gateway as pg
from apps.commerce.models import DJWallet, Payout
from apps.commerce.payout_processor import _process_single_payout

CF = dict(CASHFREE_PAYOUT_CLIENT_ID="cf_id", CASHFREE_PAYOUT_CLIENT_SECRET="cf_secret", CASHFREE_PAYOUT_PUBLIC_KEY="",
          CASHFREE_PAYOUT_ENV="sandbox")


class R:
    def __init__(self, code, body):
        self.status_code, self._b = code, body

    def json(self):
        return self._b


@pytest.fixture
def dj(dj_user):
    _, dj = dj_user
    dj.upi_id = "testdj@okhdfcbank"
    dj.payout_details = {"method": "upi"}
    dj.save(update_fields=["upi_id", "payout_details"])
    w, _ = DJWallet.objects.get_or_create(dj=dj)
    w.available_for_payout = Decimal("1200.00")
    w.pending_earnings = Decimal("1200.00")
    w.save()
    return dj


@pytest.fixture
def auto_on(settings):
    for k, v in CF.items():
        setattr(settings, k, v)
    SystemSetting.objects.update_or_create(key="auto_payouts", defaults={"value": {
        "enabled": True, "provider": "cashfree", "auto_limit": 10000, "first_needs_approval": False}})


def withdraw(dj, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        amount = _process_single_payout(dj.pk)
    assert amount == Decimal("1200.00")
    return Payout.objects.filter(dj=dj).latest("created_at")


def sent(post, host="transfers"):
    """The mocked call that went to the payouts provider (emails/Telegram also use requests.post)."""
    calls = [c for c in post.call_args_list if host in str(c.args[0] if c.args else c.kwargs.get("url", ""))]
    assert calls, "no call to the provider"
    return calls[-1]


def wallet(dj):
    return DJWallet.objects.get(dj=dj).available_for_payout


@pytest.mark.django_db
class TestDispatch:
    def test_manual_mode_leaves_it_for_admin(self, dj, django_capture_on_commit_callbacks):
        with mock.patch("requests.post") as post:
            p = withdraw(dj, django_capture_on_commit_callbacks)
        assert p.status == "pending" and not post.called

    def test_sent_and_confirmed(self, dj, auto_on, django_capture_on_commit_callbacks):
        ok = R(200, {"transfer_id": "MMPO_1", "cf_transfer_id": "CF123", "status": "SUCCESS", "status_code": "COMPLETED",
                     "transfer_utr": "UTR999"})
        with mock.patch("requests.post", return_value=ok) as post:
            p = withdraw(dj, django_capture_on_commit_callbacks)
        p.refresh_from_db()
        assert p.status == "completed" and p.utr == "UTR999" and p.provider == "cashfree" and "UTR999" in p.payment_reference
        body = json.loads(sent(post).kwargs["data"])
        assert body["transfer_id"] == f"MMPO_{p.id}" and body["transfer_mode"] == "upi"
        assert body["beneficiary_details"]["beneficiary_instrument_details"] == {"vpa": "testdj@okhdfcbank"}
        assert body["transfer_amount"] == 1200.0
        assert wallet(dj) == 0

    def test_bank_account_uses_imps(self, dj, auto_on, django_capture_on_commit_callbacks):
        dj.payout_details = {"method": "bank", "account_name": "Test D.J. 99"}
        dj.bank_account_number, dj.bank_ifsc_code = "123456789012", "HDFC0001234"
        dj.save()
        with mock.patch("requests.post", return_value=R(200, {"status": "RECEIVED"})) as post:
            p = withdraw(dj, django_capture_on_commit_callbacks)
        body = json.loads(sent(post).kwargs["data"])
        assert body["transfer_mode"] == "imps"
        assert body["beneficiary_details"]["beneficiary_name"] == "Test D J"
        assert body["beneficiary_details"]["beneficiary_instrument_details"]["bank_ifsc"] == "HDFC0001234"
        p.refresh_from_db()
        assert p.status == "processing"

    def test_refused_returns_money(self, dj, auto_on, django_capture_on_commit_callbacks):
        with mock.patch("requests.post", return_value=R(422, {"message": "Invalid VPA"})):
            p = withdraw(dj, django_capture_on_commit_callbacks)
        p.refresh_from_db()
        assert p.status == "failed" and "Invalid VPA" in p.failure_reason
        assert wallet(dj) == Decimal("1200.00")

    def test_timeout_is_never_resent_and_sync_finishes_it(self, dj, auto_on, django_capture_on_commit_callbacks):
        with mock.patch("requests.post", side_effect=requests.Timeout("slow")):
            p = withdraw(dj, django_capture_on_commit_callbacks)
        p.refresh_from_db()
        assert p.status == "processing" and wallet(dj) == 0
        # a second dispatch must not send again
        with mock.patch("requests.post") as post:
            assert pg.dispatch(p.id) == "processing"
        assert not [c for c in post.call_args_list if "cashfree" in str(c)]
        Payout.objects.filter(pk=p.pk).update(sent_at=p.sent_at - __import__("datetime").timedelta(minutes=10))
        with mock.patch("requests.get", return_value=R(200, {"status": "SUCCESS", "status_code": "COMPLETED", "transfer_utr": "U1"})):
            assert pg.sync_processing()["paid"] == 1
        p.refresh_from_db()
        assert p.status == "completed"

    def test_failure_reported_later_returns_money_once(self, dj, auto_on, django_capture_on_commit_callbacks):
        with mock.patch("requests.post", return_value=R(200, {"status": "PENDING"})):
            p = withdraw(dj, django_capture_on_commit_callbacks)
        assert pg.apply_result(p.id, {"state": "failed", "message": "Account closed"}) == "failed"
        assert pg.apply_result(p.id, {"state": "failed", "message": "Account closed"}) == "failed"
        assert wallet(dj) == Decimal("1200.00")

    def test_first_payout_waits_for_approval(self, dj, auto_on, django_capture_on_commit_callbacks):
        SystemSetting.objects.filter(key="auto_payouts").update(value={"enabled": True, "provider": "cashfree",
                                                                       "auto_limit": 10000, "first_needs_approval": True})
        with mock.patch("requests.post") as post:
            p = withdraw(dj, django_capture_on_commit_callbacks)
        p.refresh_from_db()
        assert p.status == "pending" and "First payout" in p.hold_reason and not [c for c in post.call_args_list if "cashfree" in str(c)]

    def test_above_limit_waits_for_approval(self, dj, auto_on, django_capture_on_commit_callbacks):
        SystemSetting.objects.filter(key="auto_payouts").update(value={"enabled": True, "provider": "cashfree",
                                                                       "auto_limit": 1000, "first_needs_approval": False})
        with mock.patch("requests.post") as post:
            p = withdraw(dj, django_capture_on_commit_callbacks)
        p.refresh_from_db()
        assert p.status == "pending" and "limit" in p.hold_reason and not [c for c in post.call_args_list if "cashfree" in str(c)]

    def test_admin_approves_and_sends(self, dj, auto_on, admin_user, django_capture_on_commit_callbacks):
        SystemSetting.objects.filter(key="auto_payouts").update(value={"enabled": True, "provider": "cashfree",
                                                                       "auto_limit": 1000, "first_needs_approval": False})
        with mock.patch("requests.post"):
            p = withdraw(dj, django_capture_on_commit_callbacks)
        c = Client()
        c.force_login(admin_user)
        with mock.patch("requests.post", return_value=R(200, {"status": "SUCCESS", "status_code": "COMPLETED", "transfer_utr": "U7"})):
            r = c.post("/api/v1/admin/payouts/", {"payout_id": p.id, "action": "send"})
        assert r.status_code == 302
        p.refresh_from_db()
        assert p.status == "completed"

    def test_mark_all_paid_skips_payouts_in_flight(self, dj, auto_on, admin_user, django_capture_on_commit_callbacks):
        with mock.patch("requests.post", return_value=R(200, {"status": "PENDING"})):
            p = withdraw(dj, django_capture_on_commit_callbacks)
        c = Client()
        c.force_login(admin_user)
        c.post("/api/v1/admin/payouts/", {"action": "paid_all", "reference": "BATCH"})
        p.refresh_from_db()
        assert p.status == "processing"

    def test_failed_payout_cannot_be_marked_paid(self, dj, auto_on, admin_user, django_capture_on_commit_callbacks):
        with mock.patch("requests.post", return_value=R(422, {"message": "bad"})):
            p = withdraw(dj, django_capture_on_commit_callbacks)
        c = Client()
        c.force_login(admin_user)
        c.post("/api/v1/admin/payouts/", {"payout_id": p.id, "action": "paid", "reference": "X"})
        p.refresh_from_db()
        assert p.status == "failed"


@pytest.mark.django_db
class TestWebhooks:
    def _cf_post(self, payload, secret="cf_secret", ts=None):
        raw = json.dumps(payload)
        ts = ts or str(int(time.time()))
        sig = base64.b64encode(hmac.new(secret.encode(), (ts + raw).encode(), hashlib.sha256).digest()).decode()
        return Client().post("/payouts/webhook/cashfree/", raw, content_type="application/json",
                             HTTP_X_WEBHOOK_SIGNATURE=sig, HTTP_X_WEBHOOK_TIMESTAMP=ts)

    def test_cashfree_success(self, dj, auto_on, django_capture_on_commit_callbacks):
        with mock.patch("requests.post", return_value=R(200, {"status": "PENDING"})):
            p = withdraw(dj, django_capture_on_commit_callbacks)
        r = self._cf_post({"type": "TRANSFER_SUCCESS", "data": {"transfer_id": f"MMPO_{p.id}", "cf_transfer_id": "CF1",
                                                                 "status": "SUCCESS", "transfer_utr": "UTRX"}})
        assert r.status_code == 200
        p.refresh_from_db()
        assert p.status == "completed" and p.utr == "UTRX"

    def test_cashfree_reversed_returns_money(self, dj, auto_on, django_capture_on_commit_callbacks):
        with mock.patch("requests.post", return_value=R(200, {"status": "PENDING"})):
            p = withdraw(dj, django_capture_on_commit_callbacks)
        self._cf_post({"type": "TRANSFER_REVERSED", "data": {"transfer_id": f"MMPO_{p.id}", "status": "REVERSED",
                                                             "status_description": "Beneficiary bank reversed"}})
        p.refresh_from_db()
        assert p.status == "failed" and wallet(dj) == Decimal("1200.00")

    def test_cashfree_bad_signature(self, dj, auto_on, django_capture_on_commit_callbacks):
        with mock.patch("requests.post", return_value=R(200, {"status": "PENDING"})):
            p = withdraw(dj, django_capture_on_commit_callbacks)
        r = self._cf_post({"type": "TRANSFER_SUCCESS", "data": {"transfer_id": f"MMPO_{p.id}"}}, secret="wrong")
        assert r.status_code == 401
        p.refresh_from_db()
        assert p.status == "processing"

    def test_razorpayx_webhook(self, dj, settings, django_capture_on_commit_callbacks):
        settings.RAZORPAYX_KEY_ID, settings.RAZORPAYX_KEY_SECRET = "rzp_x", "sec"
        settings.RAZORPAYX_ACCOUNT_NUMBER, settings.RAZORPAYX_WEBHOOK_SECRET = "2323230000000000", "hooksecret"
        SystemSetting.objects.update_or_create(key="auto_payouts", defaults={"value": {
            "enabled": True, "provider": "razorpayx", "auto_limit": 10000, "first_needs_approval": False}})
        with mock.patch("requests.post", return_value=R(200, {"id": "pout_1", "status": "processing"})) as post:
            p = withdraw(dj, django_capture_on_commit_callbacks)
        call = sent(post, "/v1/payouts")
        assert call.kwargs["headers"]["X-Payout-Idempotency"] == f"mixmint-payout-{p.id}"
        body = json.loads(call.kwargs["data"])
        assert body["amount"] == 120000 and body["mode"] == "UPI" and body["fund_account"]["vpa"]["address"] == "testdj@okhdfcbank"
        raw = json.dumps({"event": "payout.processed", "payload": {"payout": {"entity": {
            "id": "pout_1", "status": "processed", "utr": "RZUTR", "notes": {"payout_id": str(p.id)}}}}})
        sig = hmac.new(b"hooksecret", raw.encode(), hashlib.sha256).hexdigest()
        r = Client().post("/payouts/webhook/razorpayx/", raw, content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE=sig)
        assert r.status_code == 200
        p.refresh_from_db()
        assert p.status == "completed" and p.utr == "RZUTR"


def test_cashfree_signature_is_decryptable(settings):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    settings.CASHFREE_PAYOUT_CLIENT_ID, settings.CASHFREE_PAYOUT_PUBLIC_KEY = "cf_id", pem.replace("\n", "\\n")
    sig = pg.Cashfree._signature()
    plain = key.decrypt(base64.b64decode(sig), padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA1()), algorithm=hashes.SHA1(), label=None)).decode()
    cid, ts = plain.split(".")
    assert cid == "cf_id" and abs(int(ts) - time.time()) < 5


@pytest.mark.django_db
def test_settings_card_requires_keys(admin_user, settings):
    settings.CASHFREE_PAYOUT_CLIENT_ID = ""
    c = Client()
    c.force_login(admin_user)
    c.post("/api/v1/admin/settings/", {"action": "auto_payouts", "enabled": "on", "provider": "cashfree", "auto_limit": "5000"})
    assert not pg.config()["enabled"]
    settings.CASHFREE_PAYOUT_CLIENT_ID, settings.CASHFREE_PAYOUT_CLIENT_SECRET = "id", "sec"
    c.post("/api/v1/admin/settings/", {"action": "auto_payouts", "enabled": "on", "provider": "cashfree", "auto_limit": "5000"})
    cfg = pg.config()
    assert cfg["enabled"] and cfg["auto_limit"] == Decimal("5000") and cfg["first_needs_approval"] is False
