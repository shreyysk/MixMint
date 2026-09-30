"""
The core marketplace loop, page by page (September 2026 end-to-end audit):
apply as DJ -> admin approves -> DJ uploads (direct to R2) -> buyer pays -> DJ withdraws
-> admin pays out; refunds handled by admin.
"""

from decimal import Decimal
from unittest import mock

import boto3
import pytest
from django.test import Client, override_settings
from moto import mock_aws

R2 = dict(
    AWS_ACCESS_KEY_ID="test",
    AWS_SECRET_ACCESS_KEY="test",
    AWS_S3_ENDPOINT_URL="https://acct.r2.cloudflarestorage.com",
    R2_PRIVATE_BUCKET="raw",
    R2_PUBLIC_BUCKET="pub",
    R2_PUBLIC_URL="https://cdn.example.com",
)


def _login(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def r2_buckets():
    with mock_aws(), override_settings(**R2):
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="raw")
        s3.create_bucket(Bucket="pub")
        with mock.patch("apps.core.r2.client", lambda: s3):
            yield s3


@pytest.mark.django_db
class TestDJApplication:
    def test_form_creates_pending_application(self, user):
        c = _login(user)
        r = c.post(
            "/apply-dj/",
            {"dj_name": "Aurora", "slug": "aurora", "genres": "Techno, House", "legal_agreement_accepted": "true",
             "city": "Pune", "links": ["https://soundcloud.com/aurora/set"]},
        )
        assert r.status_code == 302
        dj = user.profile.dj_profile
        assert dj.status == "pending_review" and dj.genres == ["Techno", "House"]
        assert "Under Review" in c.get("/apply-dj/").content.decode()
        assert dj.location == "Pune" and dj.application_links == ["https://soundcloud.com/aurora/set"]

    def test_form_errors_are_shown_and_values_kept(self, user):
        r = _login(user).post("/apply-dj/", {"dj_name": "Aurora", "slug": "admin", "legal_agreement_accepted": "on"})
        html = r.content.decode()
        assert r.status_code == 400 and "reserved" in html and "Aurora" in html

    def test_admin_page_lists_and_approves(self, user, admin_user):
        _login(user).post("/apply-dj/", {"dj_name": "Aurora", "slug": "aurora", "legal_agreement_accepted": "on",
                                         "city": "Pune", "links": "https://youtu.be/abc"})
        admin = _login(admin_user)
        html = admin.get("/api/v1/admin/dj/management/").content.decode()
        assert "Aurora" in html and "Approve" in html
        dj = user.profile.dj_profile
        assert admin.post(f"/api/v1/accounts/dj/{dj.id}/approve/").status_code == 200
        user.profile.refresh_from_db()
        assert user.profile.role == "dj"
        assert "Aurora" in admin.get("/api/v1/admin/dj/management/?tab=active").content.decode()
        assert admin.get("/api/v1/admin/dashboard/").context["kpis"]["pending_djs"] == 0


@pytest.mark.django_db
class TestLandingPage:
    def test_each_role_lands_on_its_dashboard(self, user, dj_user, admin_user):
        assert _login(user).get("/start/")["Location"] == "/dashboard/"
        assert _login(dj_user[0]).get("/start/")["Location"] == "/dashboard/dj/"
        assert _login(admin_user).get("/start/")["Location"] == "/api/v1/admin/dashboard/"

    def test_home_lists_albums(self, client, album):
        assert album.title in client.get("/").content.decode()


@pytest.mark.django_db
class TestUpload:
    def test_upload_url_checks_type_and_size(self, dj_user, r2_buckets):
        c = _login(dj_user[0])
        bad = c.post("/upload/url/", {"kind": "audio", "filename": "x.exe", "size": 10}, content_type="application/json")
        assert bad.status_code == 400
        big = c.post(
            "/upload/url/", {"kind": "audio", "filename": "a.mp3", "size": 10**12}, content_type="application/json"
        )
        assert "too big" in big.json()["error"]
        ok = c.post("/upload/url/", {"kind": "audio", "filename": "My Track!.mp3", "size": 1000}, content_type="application/json")
        data = ok.json()
        assert data["key"].startswith(f"tracks/{dj_user[1].id}/") and data["key"].endswith("My-Track.mp3")
        assert "Signature" in data["url"]

    def test_buyers_cannot_get_upload_urls(self, user, r2_buckets):
        r = _login(user).post("/upload/url/", {"kind": "audio", "filename": "a.mp3", "size": 1}, content_type="application/json")
        assert r.status_code == 403

    def test_publish_track_and_album(self, dj_user, r2_buckets):
        u, dj = dj_user
        r2_buckets.put_object(Bucket="raw", Key=f"tracks/{dj.id}/abc-song.mp3", Body=b"x" * 2048)
        r2_buckets.put_object(Bucket="pub", Key=f"covers/{dj.id}/abc-c.jpg", Body=b"img")
        c = _login(u)
        with mock.patch("apps.accounts.upload_views._tag_track"):
            r = c.post(
                "/upload/",
                {
                    "kind": "track", "title": "Midnight", "price": "99", "file_key": f"tracks/{dj.id}/abc-song.mp3",
                    "cover_url": f"https://cdn.example.com/covers/{dj.id}/abc-c.jpg", "genre": "Techno", "bpm": "124",
                    "youtube_url": "https://youtu.be/dQw4w9WgXcQ", "content_responsibility_accepted": "on",
                },
            )
        assert r.status_code == 302
        from apps.tracks.models import Track

        t = Track.objects.get(title="Midnight")
        assert t.file_size == 2048 and t.file_format == "mp3" and t.cover_url.endswith("abc-c.jpg")

        r2_buckets.put_object(Bucket="raw", Key=f"albums/{dj.id}/z-pack.zip", Body=b"z" * 10)
        r = c.post(
            "/upload/",
            {
                "kind": "album", "title": "Pack", "price": "299", "file_key": f"albums/{dj.id}/z-pack.zip",
                "track_count": "8", "instagram_url": "https://www.instagram.com/reel/C0abcdEFGhi/",
                "content_responsibility_accepted": "on",
            },
        )
        assert r.status_code == 302 and "/albums/" in r["Location"]

    def test_rejects_someone_elses_file_and_missing_upload(self, dj_user, r2_buckets):
        u, dj = dj_user
        c = _login(u)
        base = {"kind": "track", "title": "T", "price": "99", "youtube_url": "https://youtu.be/dQw4w9WgXcQ",
                "content_responsibility_accepted": "on"}
        r = c.post("/upload/", {**base, "file_key": "tracks/999/other.mp3"})
        assert r.status_code == 400
        r = c.post("/upload/", {**base, "file_key": f"tracks/{dj.id}/never-uploaded.mp3"})
        assert r.status_code == 400 and "didn" in r.content.decode()

    def test_price_and_preview_rules(self, dj_user, r2_buckets):
        u, dj = dj_user
        r2_buckets.put_object(Bucket="raw", Key=f"tracks/{dj.id}/a.mp3", Body=b"x")
        c = _login(u)
        base = {"kind": "track", "title": "T", "file_key": f"tracks/{dj.id}/a.mp3", "content_responsibility_accepted": "on"}
        assert "at least" in c.post("/upload/", {**base, "price": "10", "youtube_url": "https://youtu.be/x1"}).content.decode()
        assert "preview" in c.post("/upload/", {**base, "price": "99"}).content.decode()

    @override_settings(AWS_ACCESS_KEY_ID="")
    def test_page_explains_when_storage_missing(self, dj_user):
        html = _login(dj_user[0]).get("/upload/").content.decode()
        assert "storage isn't connected" in html


@pytest.mark.django_db
class TestPayouts:
    def test_dj_saves_upi_and_bank(self, dj_user):
        u, dj = dj_user
        c = _login(u)
        c.post("/dashboard/dj/payouts/", {"method": "upi", "upi_id": "not-upi"})
        dj.refresh_from_db()
        assert not dj.upi_id
        c.post("/dashboard/dj/payouts/", {"method": "upi", "upi_id": "dj@okhdfcbank"})
        dj.refresh_from_db()
        assert dj.upi_id == "dj@okhdfcbank"
        c.post(
            "/dashboard/dj/payouts/",
            {"method": "bank", "bank_account_number": "1234 5678 9012", "bank_ifsc_code": "hdfc0001234", "account_name": "Test DJ"},
        )
        dj.refresh_from_db()
        assert dj.bank_account_number == "123456789012" and dj.bank_ifsc_code == "HDFC0001234"
        assert dj.payout_details["method"] == "bank"
        assert "••••" in c.get("/dashboard/dj/payouts/").content.decode()

    def test_admin_marks_paid_or_failed(self, dj_user, admin_user):
        from apps.commerce.models import DJWallet, Payout

        u, dj = dj_user
        wallet, _ = DJWallet.objects.get_or_create(dj=dj)
        admin = _login(admin_user)
        p1 = Payout.objects.create(dj=dj, amount=Decimal("600"), status="pending")
        assert "600" in admin.get("/api/v1/admin/payouts/").content.decode()
        admin.post("/api/v1/admin/payouts/", {"payout_id": p1.id, "action": "paid", "reference": "UTR1"})
        p1.refresh_from_db()
        assert p1.status == "completed" and p1.payment_reference == "UTR1"

        p2 = Payout.objects.create(dj=dj, amount=Decimal("700"), status="pending")
        admin.post("/api/v1/admin/payouts/", {"payout_id": p2.id, "action": "failed", "reason": "bad IFSC"})
        p2.refresh_from_db()
        wallet.refresh_from_db()
        assert p2.status == "failed" and wallet.available_for_payout == Decimal("700")
        from apps.commerce.payout_processor import retry_failed_payouts

        retry_failed_payouts()
        p2.refresh_from_db()
        assert p2.status == "failed"  # never paid twice

    def test_onboarding_saves_bio(self, dj_user):
        u, dj = dj_user
        _login(u).post(
            "/dashboard/dj/onboarding/update/",
            {"step": "payout_setup", "bio": "Techno from Pune", "location": "Pune"},
            content_type="application/json",
        )
        dj.refresh_from_db()
        assert dj.bio == "Techno from Pune" and dj.location == "Pune"


@pytest.mark.django_db
class TestRefunds:
    def test_admin_approves_manual_refund(self, purchase, admin_user, user):
        from apps.commerce.models import RefundRequest

        purchase.download_completed = True
        purchase.gateway_payment_id = "pay_1"
        purchase.payment_gateway = "razorpay"
        purchase.save()
        r = _login(user).post("/api/v1/commerce/refund/request/", {"purchase_id": purchase.id, "reason": "corrupt"})
        assert r.json()["automated"] is False
        admin = _login(admin_user)
        assert "corrupt" in admin.get("/api/v1/admin/refunds/").content.decode()
        gw = mock.Mock()
        gw.process_refund.return_value = {"refund_id": "rfnd_1"}
        with mock.patch("apps.payments.utils.get_gateway", return_value=gw):
            admin.post("/api/v1/admin/refunds/", {"refund_id": RefundRequest.objects.get().id, "action": "approve"})
        purchase.refresh_from_db()
        assert purchase.status == "refunded" and RefundRequest.objects.get().status == "processed"

    def test_admin_rejects(self, purchase, admin_user, user):
        from apps.commerce.models import RefundRequest

        purchase.download_completed = True
        purchase.save()
        _login(user).post("/api/v1/commerce/refund/request/", {"purchase_id": purchase.id, "reason": "changed mind"})
        _login(admin_user).post(
            "/api/v1/admin/refunds/", {"refund_id": RefundRequest.objects.get().id, "action": "reject", "note": "Downloaded"}
        )
        assert RefundRequest.objects.get().status == "rejected"
        purchase.refresh_from_db()
        assert purchase.status == "paid"


@pytest.mark.django_db
def test_admin_pages_use_admin_shell(admin_user, dj_user):
    c = _login(admin_user)
    for path in (
        "/api/v1/admin/dashboard/", "/api/v1/admin/dj/management/", "/api/v1/admin/payouts/", "/api/v1/admin/refunds/",
        "/api/v1/admin/content/moderation/", "/api/v1/admin/security/dashboard/",
        "/api/v1/admin/offers-pricing/", "/api/v1/admin/analytics/revenue-dashboard/",
    ):
        html = c.get(path).content.decode()
        assert 'aria-label="Admin"' in html and 'aria-current="page"' in html, path
        assert "Join the Waitlist" not in html, path  # no shop footer inside admin
    shop = _login(admin_user).get("/").content.decode()
    assert "/api/v1/admin/dashboard/" in shop  # admins get an Admin link in the shop navbar
    assert "/api/v1/admin/dashboard/" not in _login(dj_user[0]).get("/").content.decode()
