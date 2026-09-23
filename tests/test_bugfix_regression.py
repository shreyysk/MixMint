"""Regression tests for the bug-hunt fixes (money path, downloads, beat tasks)."""
import base64
import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import resolve


@pytest.mark.django_db
class TestDownloadPageUrl:
    def test_download_button_hits_real_route(self, client, user, track):
        from apps.downloads.utils import DownloadManager

        client.force_login(user)
        token = DownloadManager.generate_token(
            user.profile,
            content_id=track.id,
            content_type="track",
            access_source="purchase",
            ip_address="127.0.0.1",
            user_agent="test",
        )
        resp = client.get(f"/api/v1/downloads/page/{token.token}/")
        assert resp.status_code == 200
        assert resp.context["download_url"] == f"/api/v1/downloads/{token.token}/"
        match = resolve(resp.context["download_url"])
        assert match.func.__name__ == "download_content"


@pytest.mark.django_db
class TestPaymentLandingRoutes:
    def test_callback_success_lands_on_library(self, client, user, track, dj_user):
        from apps.commerce.models import Purchase

        _, dj = dj_user
        purchase = Purchase.objects.create(
            user=user.profile,
            content_id=track.id,
            content_type="track",
            original_price=track.price,
            price_paid=track.price,
            amount_paise=10000,
            seller=dj,
            status="pending",
            gateway_order_id="MM_TEST123",
            payment_gateway="phonepe",
        )
        fake_gateway = type(
            "G",
            (),
            {
                "get_payment_status": lambda self, oid: {
                    "success": True,
                    "status": "PAYMENT_SUCCESS",
                    "transaction_id": "T1",
                    "gateway_response": {},
                }
            },
        )()
        with patch("apps.payments.views.get_gateway", return_value=fake_gateway):
            resp = client.get("/api/v1/payments/callback/?order_id=MM_TEST123")
        assert resp.status_code == 302
        assert resp["Location"].startswith("/library/?order_id=MM_TEST123&payment=success")
        purchase.refresh_from_db()
        assert purchase.status == "paid"

    def test_callback_failure_lands_on_library(self, client, user, track, dj_user):
        from apps.commerce.models import Purchase

        _, dj = dj_user
        Purchase.objects.create(
            user=user.profile,
            content_id=track.id,
            content_type="track",
            original_price=track.price,
            price_paid=track.price,
            amount_paise=10000,
            seller=dj,
            status="pending",
            gateway_order_id="MM_TEST456",
            payment_gateway="phonepe",
        )
        fake_gateway = type(
            "G",
            (),
            {
                "get_payment_status": lambda self, oid: {
                    "success": False,
                    "status": "PAYMENT_ERROR",
                    "transaction_id": None,
                    "gateway_response": {},
                }
            },
        )()
        with patch("apps.payments.views.get_gateway", return_value=fake_gateway):
            resp = client.get("/api/v1/payments/callback/?order_id=MM_TEST456")
        assert resp.status_code == 302
        assert resp["Location"].startswith("/library/?order_id=MM_TEST456&payment=failed")


@pytest.mark.django_db
class TestWebhookAmountVerification:
    def _purchase(self, user, track, dj, order_id, paise=10000):
        from apps.commerce.models import Purchase

        return Purchase.objects.create(
            user=user.profile,
            content_id=track.id,
            content_type="track",
            original_price=track.price,
            price_paid=track.price,
            amount_paise=paise,
            seller=dj,
            status="pending",
            gateway_order_id=order_id,
            payment_gateway="phonepe",
        )

    def _phonepe_post(self, client, inner):
        from django.conf import settings as dj_settings

        salt, index = dj_settings.PHONEPE_SALT_KEY, dj_settings.PHONEPE_SALT_INDEX
        raw = base64.b64encode(json.dumps(inner).encode()).decode()
        sig = hashlib.sha256((raw + salt).encode()).hexdigest() + "###" + index
        return client.post(
            "/api/v1/payments/webhook/phonepe/",
            data=json.dumps({"response": raw}),
            content_type="application/json",
            HTTP_X_VERIFY=sig,
        )

    def test_phonepe_amount_mismatch_stays_pending(self, client, user, track, dj_user):
        _, dj = dj_user
        purchase = self._purchase(user, track, dj, "MM_MISMATCH1")
        inner = {
            "code": "PAYMENT_SUCCESS",
            "data": {"merchantTransactionId": "MM_MISMATCH1", "transactionId": "T1", "amount": 5000},
        }
        resp = self._phonepe_post(client, inner)
        assert resp.status_code == 200
        purchase.refresh_from_db()
        assert purchase.status == "pending"

    def test_phonepe_exact_amount_marks_paid(self, client, user, track, dj_user):
        _, dj = dj_user
        purchase = self._purchase(user, track, dj, "MM_MATCH1")
        inner = {
            "code": "PAYMENT_SUCCESS",
            "data": {"merchantTransactionId": "MM_MATCH1", "transactionId": "T1", "amount": 10000},
        }
        resp = self._phonepe_post(client, inner)
        assert resp.status_code == 200
        purchase.refresh_from_db()
        assert purchase.status == "paid"

    def test_phonepe_missing_transaction_id_rejected(self, client):
        inner = {"code": "PAYMENT_SUCCESS", "data": {"transactionId": "T1", "amount": 100}}
        assert self._phonepe_post(client, inner).status_code == 400

    def _razorpay_post(self, client, payload):
        from django.conf import settings as dj_settings

        body = json.dumps(payload)
        sig = hmac.new(dj_settings.RAZORPAY_KEY_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
        return client.post(
            "/api/v1/payments/webhook/razorpay/",
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )

    def test_razorpay_amount_mismatch_stays_pending(self, client, user, track, dj_user):
        from apps.commerce.models import Purchase

        _, dj = dj_user
        purchase = Purchase.objects.create(
            user=user.profile,
            content_id=track.id,
            content_type="track",
            original_price=track.price,
            price_paid=track.price,
            amount_paise=10000,
            seller=dj,
            status="pending",
            gateway_order_id="order_MISMATCH",
            payment_gateway="razorpay",
        )
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {"order_id": "order_MISMATCH", "id": "pay_1", "status": "captured", "amount": 5000}
                }
            },
        }
        assert self._razorpay_post(client, payload).status_code == 200
        purchase.refresh_from_db()
        assert purchase.status == "pending"

    def test_razorpay_exact_amount_marks_paid(self, client, user, track, dj_user):
        from apps.commerce.models import Purchase

        _, dj = dj_user
        purchase = Purchase.objects.create(
            user=user.profile,
            content_id=track.id,
            content_type="track",
            original_price=track.price,
            price_paid=track.price,
            amount_paise=10000,
            seller=dj,
            status="pending",
            gateway_order_id="order_MATCH",
            payment_gateway="razorpay",
        )
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {"entity": {"order_id": "order_MATCH", "id": "pay_2", "status": "captured", "amount": 10000}}
            },
        }
        assert self._razorpay_post(client, payload).status_code == 200
        purchase.refresh_from_db()
        assert purchase.status == "paid"


@pytest.mark.django_db
class TestPaymentFailureGuard:
    def test_late_failure_cannot_unpay(self, user, track, dj_user):
        from apps.commerce.models import Purchase
        from apps.payments.views import handle_payment_failure

        _, dj = dj_user
        purchase = Purchase.objects.create(
            user=user.profile,
            content_id=track.id,
            content_type="track",
            original_price=track.price,
            price_paid=track.price,
            seller=dj,
            status="paid",
            gateway_order_id="MM_LATEFAIL",
        )
        handle_payment_failure(purchase, {"gateway_response": {}})
        purchase.refresh_from_db()
        assert purchase.status == "paid"

    def test_gateway_crash_redirects_to_pending(self, client, user, track, dj_user):
        from apps.commerce.models import Purchase

        _, dj = dj_user
        Purchase.objects.create(
            user=user.profile,
            content_id=track.id,
            content_type="track",
            original_price=track.price,
            price_paid=track.price,
            seller=dj,
            status="pending",
            gateway_order_id="MM_CRASH",
            payment_gateway="phonepe",
        )

        class Boom:
            def get_payment_status(self, oid):
                raise TimeoutError("gateway down")

        with patch("apps.payments.views.get_gateway", return_value=Boom()):
            resp = client.get("/api/v1/payments/callback/?order_id=MM_CRASH")
        assert resp.status_code == 302
        assert resp["Location"].startswith("/library/?order_id=MM_CRASH&payment=pending")


@pytest.mark.django_db
class TestAlbumExternalFlow:
    def test_album_external_issue_and_download(self, client, user, album, dj_user, tmp_path):
        from apps.commerce.models import Purchase

        _, dj = dj_user
        album.is_external_link = True
        album.external_link_url = "https://drive.google.com/file/d/ALBUM1234567890/view"
        album.external_link_provider = "google_drive"
        album.save()
        Purchase.objects.create(
            user=user.profile,
            content_id=album.id,
            content_type="album",
            original_price=album.price,
            price_paid=album.price,
            seller=dj,
            status="paid",
        )
        client.force_login(user)
        resp = client.post(
            "/api/v1/downloads/external/issue/",
            {"content_type": "album", "content_id": album.id},
            content_type="application/json",
        )
        assert resp.status_code == 201, resp.content[:300]
        token = resp.json()["token"]
        cached = tmp_path / "album.bin"
        cached.write_bytes(b"ALB" * 100)
        with patch("apps.downloads.external_views.fetch_from_source", return_value=str(cached)):
            dl_resp = client.get(f"/api/v1/downloads/external/{token}/")
        assert dl_resp.status_code == 200
        assert 'filename="Test Album.zip"' in dl_resp["Content-Disposition"]


@pytest.mark.django_db
class TestRevenueIdempotency:
    def test_double_complete_credits_once(self, user, track, dj_user):
        from apps.commerce.models import Invoice, LedgerEntry, Purchase
        from apps.commerce.services import MonetizationService

        _, dj = dj_user
        purchase = Purchase.objects.create(
            user=user.profile,
            content_id=track.id,
            content_type="track",
            original_price=track.price,
            price_paid=Decimal("100.00"),
            amount_paise=10000,
            seller=dj,
            status="paid",
        )
        MonetizationService.complete_purchase(purchase)
        MonetizationService.complete_purchase(purchase)  # retry/race duplicate
        wallet = dj.wallet
        wallet.refresh_from_db()
        assert wallet.total_earnings == Decimal("85.00")
        assert Invoice.objects.filter(purchase=purchase).count() == 1
        assert LedgerEntry.objects.filter(wallet=wallet).count() == 1


@pytest.mark.django_db
class TestBeatTaskPaths:
    def test_all_beat_tasks_resolve(self):
        from config.celery import app as cap

        cap.autodiscover_tasks(force=True)
        for task_path in [
            "apps.commerce.tasks.run_payout_cron",
            "apps.downloads.tasks.cleanup_expired_tokens",
            "apps.downloads.tasks.cleanup_expired_downloads",
            "apps.tracks.tasks.update_weekly_sales",
            "apps.tracks.tasks.detect_offload_candidates",
        ]:
            assert task_path in cap.tasks, task_path

    def test_migration_task_rows_point_at_real_tasks(self):
        from django_celery_beat.models import PeriodicTask

        for name in [
            "Process Pro renewals and storage overage",
            "Cleanup expired download tokens",
            "Update weekly sales for tracks",
            "Detect offload candidates",
        ]:
            row = PeriodicTask.objects.filter(name=name).first()
            if row is not None:
                assert ".management.commands." not in row.task, name
