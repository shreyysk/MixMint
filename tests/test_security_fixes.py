"""
Regression tests for the September 2026 audit. Each test pins a bug that was
exploitable before the fix (see FIXES.md for the full list).
"""

import hashlib
import hmac
import json
from decimal import Decimal
from unittest import mock

import pytest
from django.test import Client


def _login(user, **kw):
    c = Client(**kw)
    c.force_login(user)
    return c


class FakeGateway:
    """Records the amount it was asked to charge. Behaves like PhonePe (redirect)."""

    name = "phonepe"
    calls = []

    def create_order(self, amount_paise, currency="INR", order_id=None, metadata=None):
        FakeGateway.calls.append(amount_paise)
        return {"redirect_url": "https://pay.example/x", "order_id": order_id, "gateway_order_id": order_id}


@pytest.fixture
def fake_gateway():
    FakeGateway.calls = []
    with mock.patch("apps.payments.views.get_gateway", return_value=FakeGateway()):
        yield FakeGateway


def _pending(user, track, dj):
    from apps.commerce.models import Purchase

    return Purchase.objects.create(
        user=user.profile,
        content_id=track.id,
        content_type="track",
        original_price=track.price,
        price_paid=track.price,
        seller=dj,
        status="pending",
        gateway_order_id="MM_PENDING",
    )


# --------------------------------------------------------------------- access
@pytest.mark.django_db
class TestOwnershipAndAccess:
    def test_pending_purchase_does_not_grant_download(self, user, track, dj_user):
        _pending(user, track, dj_user[1])
        r = _login(user).post(f"/api/v1/tracks/{track.id}/download-token/", {}, content_type="application/json")
        assert r.status_code == 403

    def test_paid_purchase_grants_download(self, user, track, purchase):
        r = _login(user).post(f"/api/v1/tracks/{track.id}/download-token/", {}, content_type="application/json")
        assert r.status_code == 200
        assert r.json()["download_url"].startswith("/api/v1/downloads/")

    def test_buyer_cannot_delete_or_edit_track(self, user, track):
        c = _login(user)
        assert c.delete(f"/api/v1/tracks/{track.id}/").status_code == 403
        r = c.patch(f"/api/v1/tracks/{track.id}/", json.dumps({"title": "x"}), content_type="application/json")
        assert r.status_code == 403
        track.refresh_from_db()
        assert track.title == "Test Track" and not track.is_deleted

    def test_owner_delete_is_soft(self, dj_user, track):
        c = _login(dj_user[0])
        assert c.delete(f"/api/v1/tracks/{track.id}/").status_code == 204
        track.refresh_from_db()
        assert track.is_deleted and not track.is_active

    def test_buyer_cannot_touch_albums(self, user, album):
        c = _login(user)
        r = c.patch(f"/api/v1/albums/{album.id}/", json.dumps({"title": "x"}), content_type="application/json")
        assert r.status_code == 403
        assert c.delete(f"/api/v1/albums/{album.id}/").status_code == 403
        album.refresh_from_db()
        assert album.title == "Test Album" and not album.is_deleted

    def test_albums_are_publicly_browsable(self, album):
        assert Client().get(f"/api/v1/albums/{album.id}/").status_code == 200

    def test_dj_cannot_create_track_for_another_dj(self, dj_user, pro_dj_user):
        _, other = pro_dj_user
        r = _login(dj_user[0]).post(
            "/api/v1/tracks/",
            json.dumps(
                {
                    "dj": other.id,
                    "title": "Hijack",
                    "price": "50.00",
                    "file_key": "t/h.wav",
                    "preview_type": "youtube",
                    "youtube_url": "https://youtube.com/watch?v=abcdefghijk",
                }
            ),
            content_type="application/json",
        )
        assert r.status_code == 201, r.content
        from apps.tracks.models import Track

        assert Track.objects.get(title="Hijack").dj == dj_user[1]

    def test_profile_privilege_escalation_blocked(self, user):
        c = _login(user)
        r = c.patch(
            f"/api/v1/accounts/profiles/{user.pk}/",
            json.dumps({"role": "admin", "is_pro_dj": True, "full_name": "New Name"}),
            content_type="application/json",
        )
        assert r.status_code == 200
        user.profile.refresh_from_db()
        assert user.profile.role == "user" and not user.profile.is_pro_dj
        assert user.profile.full_name == "New Name"

    def test_dj_directory_is_read_only_and_hides_bank_details(self, dj_user):
        _, dj = dj_user
        dj.bank_account_number = "123456789"
        dj.pan_number = "ABCDE1234F"
        dj.payout_otp_secret = "SECRETSECRET"
        dj.save()
        c = Client()
        data = c.get(f"/api/v1/accounts/djs/{dj.slug}/").json()
        for field in ("bank_account_number", "pan_number", "payout_otp_secret", "upi_id", "payout_details"):
            assert field not in data
        assert c.patch(f"/api/v1/accounts/djs/{dj.slug}/", {}, content_type="application/json").status_code in (
            401,
            403,
            405,
        )
        assert c.delete(f"/api/v1/accounts/djs/{dj.slug}/").status_code in (401, 403, 405)

    def test_purchase_api_hides_gateway_payloads(self, user, purchase):
        rows = _login(user).get("/api/v1/commerce/purchases/").json()
        row = rows["results"][0] if isinstance(rows, dict) else rows[0]
        assert "gateway_response" not in row and "external_link_url" not in row

    def test_legacy_verify_endpoint_cannot_mint_paid_purchase(self, user, track):
        from apps.commerce.models import Purchase

        r = _login(user).post(
            "/api/v1/commerce/verify-purchase/",
            json.dumps({"content_type": "track", "content_id": track.id, "gateway": "phonepe"}),
            content_type="application/json",
        )
        assert r.status_code in (400, 404)
        assert not Purchase.objects.filter(status="paid").exists()


# ------------------------------------------------------------------- pricing
@pytest.mark.django_db
class TestPricing:
    def test_fake_redownload_flag_rejected(self, user, track, platform_settings, fake_gateway):
        r = _login(user).post(
            "/api/v1/payments/initiate/",
            json.dumps({"content_id": track.id, "content_type": "track", "is_redownload": True}),
            content_type="application/json",
        )
        assert r.status_code == 400
        assert fake_gateway.calls == []

    def test_full_price_charged(self, user, track, platform_settings, fake_gateway):
        r = _login(user).post(
            "/api/v1/payments/initiate/",
            json.dumps({"content_id": track.id, "content_type": "track"}),
            content_type="application/json",
        )
        assert r.status_code == 200, r.content
        assert fake_gateway.calls == [10000]

    def test_cart_charges_paise_not_100x(self, user, track, platform_settings, fake_gateway):
        from apps.commerce.models import Cart, CartItem, Purchase

        cart = Cart.objects.create(user=user.profile)
        CartItem.objects.create(cart=cart, content_type="track", content_id=track.id, price=10000)
        r = _login(user).post(
            "/api/v1/payments/cart-checkout/", json.dumps({"cart_id": str(cart.id)}), content_type="application/json"
        )
        assert r.status_code == 200, r.content
        assert fake_gateway.calls == [10000]
        p = Purchase.objects.get(cart_id=cart.id)
        assert p.amount_paise == 10000 and p.price_paid == Decimal("100.00")

    def test_cart_discount_lines_sum_to_charge(self, user, dj_user, platform_settings, fake_gateway):
        from apps.commerce.models import Cart, CartItem, Purchase
        from apps.tracks.models import Track

        cart = Cart.objects.create(user=user.profile)
        for i in range(3):
            t = Track.objects.create(
                dj=dj_user[1],
                title=f"T{i}",
                price=Decimal("99.00"),
                file_key=f"t/{i}.wav",
                youtube_url="https://youtube.com/watch?v=abcdefghijk",
            )
            CartItem.objects.create(cart=cart, content_type="track", content_id=t.id, price=9900)
        r = _login(user).post(
            "/api/v1/payments/cart-checkout/", json.dumps({"cart_id": str(cart.id)}), content_type="application/json"
        )
        assert r.status_code == 200
        charged = fake_gateway.calls[0]
        assert charged == 29700 - (29700 * 5 + 50) // 100
        assert sum(Purchase.objects.filter(cart_id=cart.id).values_list("amount_paise", flat=True)) == charged

    def test_self_purchase_blocked(self, dj_user, track, platform_settings, fake_gateway):
        r = _login(dj_user[0]).post(
            "/api/v1/payments/initiate/",
            json.dumps({"content_id": track.id, "content_type": "track"}),
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_redownload_price_no_crash(self, user, track, purchase):
        from datetime import timedelta

        from django.utils import timezone

        from apps.commerce.models import Purchase

        Purchase.objects.filter(pk=purchase.pk).update(
            download_completed=True, paid_at=timezone.now() - timedelta(days=8)  # past the 7-day free window
        )
        r = _login(user).post(f"/api/v1/tracks/{track.id}/download-token/", {}, content_type="application/json")
        assert r.status_code == 402
        assert r.json()["redownload_price"] == "50.00"


# ------------------------------------------------------------------ payments
@pytest.mark.django_db
class TestPaymentCompletion:
    def test_phonepe_urls_point_at_real_routes(self, settings):
        from django.urls import resolve

        from apps.payments.phonepe import PhonePeGateway

        settings.BASE_URL = "https://mixmint.site"
        with mock.patch("apps.payments.phonepe.requests.post") as post:
            post.return_value.json.return_value = {"success": False, "message": "x"}
            with pytest.raises(Exception):
                PhonePeGateway().create_order(1000, order_id="MM_X")
            import base64

            payload = json.loads(base64.b64decode(post.call_args.kwargs["json"]["request"]))
        for key in ("redirectUrl", "callbackUrl"):
            path = payload[key].replace("https://mixmint.site", "").split("?")[0]
            resolve(path)  # raises Resolver404 if the route doesn't exist

    def test_callback_and_webhook_credit_once(self, user, track, dj_user):
        from apps.commerce.models import DJWallet, Invoice
        from apps.payments.services import complete_order

        p = _pending(user, track, dj_user[1])
        p.amount_paise = 10000
        p.save()
        assert complete_order("MM_PENDING", "T1", {}, 10000) == "ok"
        assert complete_order("MM_PENDING", "T1", {}, 10000) == "already_processed"
        p.refresh_from_db()
        assert p.status == "paid"
        assert Invoice.objects.filter(purchase=p).count() == 1
        assert DJWallet.objects.get(dj=dj_user[1]).total_earnings == Decimal("85.00")

    def test_amount_mismatch_not_fulfilled(self, user, track, dj_user):
        from apps.payments.services import complete_order

        p = _pending(user, track, dj_user[1])
        p.amount_paise = 10000
        p.save()
        assert complete_order("MM_PENDING", "T1", {}, 100) == "amount_mismatch"
        p.refresh_from_db()
        assert p.status == "pending"

    def test_razorpay_webhook_needs_webhook_secret(self, client, user, track, dj_user, settings):
        from apps.commerce.models import Purchase

        p = _pending(user, track, dj_user[1])
        Purchase.objects.filter(pk=p.pk).update(gateway_order_id="order_ABC", amount_paise=10000)
        body = json.dumps(
            {
                "event": "payment.captured",
                "payload": {
                    "payment": {
                        "entity": {"order_id": "order_ABC", "id": "pay_1", "amount": 10000, "status": "captured"}
                    }
                },
            }
        )
        bad = hmac.new(b"rzp_secret_test", body.encode(), hashlib.sha256).hexdigest()
        r = client.post(
            "/api/v1/payments/webhook/razorpay/", body, content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE=bad
        )
        assert r.status_code == 401
        good = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
        r = client.post(
            "/api/v1/payments/webhook/razorpay/", body, content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE=good
        )
        assert r.status_code == 200
        p.refresh_from_db()
        assert p.status == "paid"

    def test_authorized_event_is_not_a_failure(self, client, user, track, dj_user, settings):
        from apps.commerce.models import Purchase

        p = _pending(user, track, dj_user[1])
        Purchase.objects.filter(pk=p.pk).update(gateway_order_id="order_AUTH")
        body = json.dumps(
            {
                "event": "payment.authorized",
                "payload": {
                    "payment": {
                        "entity": {"order_id": "order_AUTH", "id": "pay_2", "amount": 10000, "status": "authorized"}
                    }
                },
            }
        )
        sig = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
        client.post(
            "/api/v1/payments/webhook/razorpay/", body, content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE=sig
        )
        p.refresh_from_db()
        assert p.status == "pending"

    def test_phonepe_webhook_verified_with_phonepe_even_if_default_is_razorpay(self, client, settings):
        import base64

        settings.DEFAULT_PAYMENT_GATEWAY = "razorpay"
        payload = base64.b64encode(
            json.dumps({"code": "PAYMENT_ERROR", "data": {"merchantTransactionId": "MM_NONE"}}).encode()
        ).decode()
        sig = hashlib.sha256((payload + settings.PHONEPE_SALT_KEY).encode()).hexdigest() + "###1"
        r = client.post(
            "/api/v1/payments/webhook/phonepe/",
            json.dumps({"response": payload}),
            content_type="application/json",
            HTTP_X_VERIFY=sig,
        )
        assert r.status_code == 200

    def test_insurance_order_activates_only_after_payment(self, user, purchase, fake_gateway):
        from datetime import timedelta

        from django.utils import timezone

        from apps.commerce.models import Purchase
        from apps.downloads.models import DownloadInsurance
        from apps.payments.services import complete_order

        Purchase.objects.filter(pk=purchase.pk).update(paid_at=timezone.now() - timedelta(days=2))
        with mock.patch("apps.payments.utils.get_gateway", return_value=FakeGateway()):
            r = _login(user).post(f"/api/v1/commerce/insurance/{purchase.id}/buy/", {}, content_type="application/json")
        assert r.status_code == 200, r.content
        assert FakeGateway.calls[-1] == 4900
        ins = DownloadInsurance.objects.get(purchase=purchase)
        assert ins.status == "pending"
        assert complete_order(ins.payment_id, "T9", {}, 4900) == "ok"
        ins.refresh_from_db()
        assert ins.status == "active"


# ----------------------------------------------------------------- downloads
@pytest.mark.django_db
class TestDownloadTokens:
    def test_proxy_ip_is_consistent_and_does_not_freeze(self, user, track, purchase, settings):
        settings.NUM_PROXIES = 1
        c = _login(user, REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4")
        url = c.post(f"/api/v1/tracks/{track.id}/download-token/", {}, content_type="application/json").json()[
            "download_url"
        ]
        with mock.patch("apps.downloads.views.boto3.client") as client_factory:
            body = mock.MagicMock()
            body.__enter__.return_value.read.side_effect = [b"abc", b""]
            client_factory.return_value.get_object.return_value = {
                "ContentLength": 3,
                "Body": body,
                "ContentType": "audio/wav",
            }
            r = c.get(url)
            b"".join(r.streaming_content)
        user.profile.refresh_from_db()
        assert r.status_code == 200
        assert not user.profile.is_frozen

    def test_spoofed_xff_does_not_change_client_ip(self, rf, settings):
        from apps.core.net import get_client_ip

        settings.NUM_PROXIES = 1
        req = rf.get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="6.6.6.6, 1.2.3.4")
        assert get_client_ip(req) == "1.2.3.4"
        settings.NUM_PROXIES = 0
        assert get_client_ip(req) == "10.0.0.1"

    def test_token_single_use(self, user, track, purchase):
        from apps.downloads.utils import DownloadManager

        tok = DownloadManager.generate_token(user.profile, track.id, "track", "purchase", "1.1.1.1", "ua")
        DownloadManager.validate_and_use(tok.token, "1.1.1.1")
        with pytest.raises(ValueError):
            DownloadManager.validate_and_use(tok.token, "1.1.1.1")

    def test_network_change_alone_does_not_freeze(self, user, track, purchase):
        from apps.downloads.utils import DownloadManager

        tok = DownloadManager.generate_token(user.profile, track.id, "track", "purchase", "1.1.1.1", "ua", "dev1")
        with pytest.raises(ValueError):
            DownloadManager.validate_and_use(tok.token, "2.2.2.2", "dev1")
        user.profile.refresh_from_db()
        assert not user.profile.is_frozen

    def test_shared_link_freezes(self, user, track, purchase):
        from apps.downloads.utils import DownloadManager

        tok = DownloadManager.generate_token(user.profile, track.id, "track", "purchase", "1.1.1.1", "ua", "dev1")
        with pytest.raises(ValueError):
            DownloadManager.validate_and_use(tok.token, "2.2.2.2", "dev2")
        user.profile.refresh_from_db()
        assert user.profile.is_frozen


# --------------------------------------------------------------------- pages
@pytest.mark.django_db
class TestPagesThatCrashed:
    def test_sitemap(self, client, track, album, dj_user):
        r = client.get("/sitemap.xml")
        assert r.status_code == 200
        assert f"/tracks/{track.id}/".encode() in r.content
        assert f"/dj/{dj_user[1].slug}/".encode() in r.content

    def test_mobile_home_and_track(self, client, track):
        assert client.get("/api/v1/platform/m/home/").status_code == 200
        assert client.get(f"/api/v1/platform/m/track/{track.id}/").status_code == 200

    def test_dj_onboarding_status(self, dj_user):
        assert _login(dj_user[0]).get("/api/v1/commerce/dj/onboarding/").status_code == 200

    def test_domain_status_for_non_dj(self, user):
        assert _login(user).get("/dashboard/dj/domain/status/").status_code == 403

    def test_2fa_enable_never_reveals_confirmed_secret(self, dj_user):
        _, dj = dj_user
        c = _login(dj_user[0])
        first = c.get("/dashboard/dj/2fa/enable/").json()
        assert first["status"] == "pending" and first["secret"]
        dj.payout_otp_secret = first["secret"]
        dj.save()
        again = c.get("/dashboard/dj/2fa/enable/").json()
        assert "secret" not in again

    def test_paused_store_page(self, client, dj_user):
        u, dj = dj_user
        u.profile.store_paused = True
        u.profile.save()
        assert client.get(f"/dj/{dj.slug}/").status_code == 200

    def test_checkout_link_redirects_to_cart(self, client):
        r = client.get("/checkout/")
        assert r.status_code == 302 and r["Location"] == "/cart/"

    def test_deleted_track_page_404(self, client, track):
        track.is_deleted = True
        track.save()
        assert client.get(f"/tracks/{track.id}/").status_code == 404

    def test_search_routes_not_shadowed(self):
        from django.urls import resolve

        assert resolve("/api/v1/tracks/search/").url_name == "advanced_search"
        assert resolve("/api/v1/tracks/popular/").url_name == "popular_this_week"

    def test_cron_jobs_all_run(self, settings, client):
        from apps.core.cron_views import JOBS

        settings.CRON_SECRET = "s3cret"
        for job in JOBS:
            r = client.get(f"/cron/{job}/", HTTP_X_CRON_SECRET="s3cret")
            assert r.status_code == 200, (job, r.content)


# ---------------------------------------------------------------- auth abuse
@pytest.mark.django_db
class TestBruteForce:
    def test_login_is_rate_limited(self, user):
        c = Client()
        for _ in range(8):
            c.post("/login/", {"email": "buyer@example.com", "password": "wrong"})
        r = c.post("/login/", {"email": "buyer@example.com", "password": "StrongPass123!"})
        assert r.status_code == 429

    def test_bundle_cannot_include_other_djs_tracks(self, dj_user, pro_dj_user):
        from apps.commerce.models import Bundle
        from apps.tracks.models import Track

        other = Track.objects.create(
            dj=pro_dj_user[1],
            title="Theirs",
            price=Decimal("50.00"),
            file_key="t/x.wav",
            youtube_url="https://youtube.com/watch?v=abcdefghijk",
        )
        _login(dj_user[0]).post(
            "/dashboard/bundles/create/", {"title": "B", "price": "10", "tracks": [other.id, other.id]}
        )
        assert not Bundle.objects.exists()


# --- Launch prep: Vercel cron auth + Razorpay test mode -------------------------------------
@pytest.mark.django_db
def test_cron_accepts_vercel_bearer_secret(client, settings):
    settings.CRON_SECRET = "s3cret-value"
    assert client.get("/cron/cleanup/", HTTP_AUTHORIZATION="Bearer wrong").status_code == 403
    assert client.get("/cron/nope/", HTTP_AUTHORIZATION="Bearer s3cret-value").status_code == 404


@pytest.mark.django_db
def test_test_mode_banner(client, settings):
    from django.core.cache import cache

    cache.clear()
    settings.DEFAULT_PAYMENT_GATEWAY = "razorpay"
    settings.PAYMENTS_TEST_MODE = True
    assert b"TEST MODE" in client.get("/").content
    cache.clear()
    settings.PAYMENTS_TEST_MODE = False
    assert b"TEST MODE" not in client.get("/").content


@pytest.mark.django_db
def test_bundle_delete_is_owner_only(dj_user, user):
    from apps.commerce.models import Bundle

    bundle = Bundle.objects.create(dj=dj_user[1], title="Pack", price=Decimal("99.00"))
    assert _login(user).post(f"/dashboard/bundles/{bundle.id}/delete/").status_code in (302, 403)
    bundle.refresh_from_db()
    assert not bundle.is_deleted
    assert _login(dj_user[0]).post(f"/dashboard/bundles/{bundle.id}/delete/").status_code == 302
    bundle.refresh_from_db()
    assert bundle.is_deleted


@pytest.mark.django_db
def test_2fa_setup_returns_qr(dj_user):
    r = _login(dj_user[0]).get("/dashboard/dj/2fa/enable/")
    assert r.status_code == 200
    assert r.json()["qr_data_uri"].startswith("data:image/svg+xml")


@pytest.mark.django_db(transaction=True)
def test_payout_sends_email(dj_user, mailoutbox, settings):
    from apps.commerce.models import DJWallet
    from apps.commerce.payout_processor import _process_single_payout

    settings.MIN_PAYOUT_THRESHOLD = 500
    DJWallet.objects.update_or_create(
        dj=dj_user[1], defaults={"available_for_payout": Decimal("600.00"), "pending_earnings": Decimal("600.00")}
    )
    assert _process_single_payout(dj_user[1].id) == Decimal("600.00")
    assert any("Payout" in m.subject for m in mailoutbox)


@pytest.mark.django_db
@pytest.mark.parametrize("size,expect_redirect", [(100 * 1024 * 1024, True), (1024, False)])
def test_auto_delivery_hands_large_files_to_signed_url(user, track, purchase, settings, size, expect_redirect):
    from apps.commerce.models import Purchase

    settings.DOWNLOAD_DELIVERY = "auto"
    settings.DOWNLOAD_PROXY_MAX_MB = 40
    c = _login(user)
    url = c.post(f"/api/v1/tracks/{track.id}/download-token/", {}, content_type="application/json").json()[
        "download_url"
    ]
    with mock.patch("apps.downloads.views.boto3.client") as client_factory:
        s3 = client_factory.return_value
        s3.head_object.return_value = {"ContentLength": size}
        s3.generate_presigned_url.return_value = "https://r2.example/signed?x=1"
        body = mock.MagicMock()
        body.__enter__.return_value.read.side_effect = [b"abc", b""]
        s3.get_object.return_value = {"ContentLength": 3, "Body": body, "ContentType": "audio/mpeg"}
        r = c.get(url)
        if not expect_redirect:
            b"".join(r.streaming_content)
    if expect_redirect:
        assert r.status_code == 302 and r["Location"].startswith("https://r2.example/")
        assert Purchase.objects.get(pk=purchase.pk).download_completed
        assert c.get(url).status_code == 403  # token is single-use
    else:
        assert r.status_code == 200
