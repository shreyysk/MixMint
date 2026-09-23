"""External-source downloads: secure token flow, no source URL exposure, cleanup."""

import os
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import Client


@pytest.mark.django_db
class TestExternalSourceSecurity:
    def test_source_url_never_in_serializer(self, dj_user):
        from apps.tracks.models import Track
        from apps.tracks.serializers import TrackSerializer

        _, dj = dj_user
        track = Track.objects.create(
            dj=dj,
            title="Secret Source Track",
            price=Decimal("99.00"),
            file_key="tracks/secret.wav",
            preview_type="youtube",
            youtube_url="https://youtube.com/watch?v=abc123",
            is_external_link=True,
            source_url="https://drive.google.com/file/d/SECRET123/view",
            source_type="gdrive",
        )
        data = TrackSerializer(track).data
        blob = str(data)
        assert "SECRET123" not in blob
        assert "source_url" not in data
        assert "source_type" not in data
        assert "external_link_url" not in data

    def test_issue_requires_purchase(self, client, user, track, dj_user):
        track.is_external_link = True
        track.source_url = "https://drive.google.com/file/d/FAKEID1234567890/view"
        track.source_type = "gdrive"
        track.save()
        client.force_login(user)
        resp = client.post(
            "/api/v1/downloads/external/issue/",
            {"content_type": "track", "content_id": track.id},
            content_type="application/json",
        )
        assert resp.status_code == 403

    def test_issue_and_download_single_use(self, client, user, track, dj_user, tmp_path):
        from apps.commerce.models import Purchase

        _, dj = dj_user
        track.is_external_link = True
        track.source_url = "https://drive.google.com/file/d/FAKEID1234567890/view"
        track.source_type = "gdrive"
        track.save()
        Purchase.objects.create(
            user=user.profile,
            content_id=track.id,
            content_type="track",
            original_price=track.price,
            price_paid=track.price,
            seller=dj,
            status="paid",
        )
        client.force_login(user)
        resp = client.post(
            "/api/v1/downloads/external/issue/",
            {"content_type": "track", "content_id": track.id},
            content_type="application/json",
        )
        assert resp.status_code == 201, resp.content[:300]
        token = resp.json()["token"]
        assert "drive.google.com" not in str(resp.json())

        cached = tmp_path / "song.mp3"
        cached.write_bytes(b"FAKEAUDIO" * 100)
        with patch("apps.downloads.external_views.fetch_from_source", return_value=str(cached)):
            dl_resp = client.get(f"/api/v1/downloads/external/{token}/")
        assert dl_resp.status_code == 200
        assert b"FAKEAUDIO" in b"".join(dl_resp.streaming_content)
        assert "drive.google.com" not in str(dl_resp.get("Content-Disposition", ""))

        # Single-use: second hit must be rejected.
        dl_resp2 = client.get(f"/api/v1/downloads/external/{token}/")
        assert dl_resp2.status_code == 403

    def test_other_user_cannot_use_token(self, user, second_user, track, dj_user):
        from apps.downloads.models import DownloadToken
        from apps.commerce.models import Purchase

        _, dj = dj_user
        Purchase.objects.create(
            user=user.profile,
            content_id=track.id,
            content_type="track",
            original_price=track.price,
            price_paid=track.price,
            seller=dj,
            status="paid",
        )
        token = DownloadToken.create_external_token(user.profile, "track", track.id)
        c2 = Client()
        c2.force_login(second_user)
        resp = c2.get(f"/api/v1/downloads/external/{token.token}/")
        assert resp.status_code == 403

    def test_expired_token_rejected(self, client, user, track, dj_user):
        from apps.downloads.models import DownloadToken

        token = DownloadToken.create_external_token(user.profile, "track", track.id, expiry_minutes=-1)
        assert not token.is_active
        client.force_login(user)
        resp = client.get(f"/api/v1/downloads/external/{token.token}/")
        assert resp.status_code == 403

    def test_cleanup_removes_cached_file(self, user, track, tmp_path):
        from apps.downloads.models import DownloadToken
        from apps.downloads.tasks import cleanup_expired_downloads

        cached = tmp_path / "stale.mp3"
        cached.write_bytes(b"x" * 64)
        token = DownloadToken.create_external_token(user.profile, "track", track.id, expiry_minutes=-1)
        token.cached_file_path = str(cached)
        token.save(update_fields=["cached_file_path"])
        result = cleanup_expired_downloads()
        token.refresh_from_db()
        assert token.cached_file_path == ""
        assert not os.path.exists(str(cached))
        assert "Cleaned 1" in result

    def test_external_only_track_needs_no_r2_file(self, dj_user):
        from apps.tracks.models import Track

        _, dj = dj_user
        track = Track.objects.create(
            dj=dj,
            title="Drive Only Track",
            price=Decimal("49.00"),
            file_key="",
            preview_type="youtube",
            youtube_url="https://youtube.com/watch?v=ext123",
            is_external_link=True,
            source_url="https://drive.google.com/file/d/ABC123xyz_-/view",
            source_type="gdrive",
        )
        assert track.id is not None

    def test_gdrive_id_parser(self):
        from apps.downloads.source_fetch import extract_gdrive_id

        assert extract_gdrive_id("https://drive.google.com/file/d/ABC123xyz_-/view") == "ABC123xyz_-"
        assert extract_gdrive_id("https://drive.google.com/open?id=ABC123xyz_-") == "ABC123xyz_-"
        assert extract_gdrive_id("https://example.com/nope") is None

    def test_shared_cache_key_stable_per_source(self, track):
        from apps.downloads import external_cache

        k1 = external_cache.cache_key_for(track.id, "https://drive.google.com/file/d/X/view")
        k2 = external_cache.cache_key_for(track.id, "https://drive.google.com/file/d/X/view")
        k3 = external_cache.cache_key_for(track.id, "https://drive.google.com/file/d/Y/view")
        assert k1 == k2
        assert k1 != k3
        assert k1.startswith("external_cache/")
        assert "drive.google" not in k1  # key leaks nothing about the source

    def test_r2_disabled_with_dummy_creds(self):
        from apps.downloads import external_cache

        assert external_cache.is_configured() is False  # test settings use dummy creds
        assert external_cache.get_fresh_key(1, "https://drive.google.com/file/d/X/view") is None

    def test_second_buyer_reuses_shared_cache(self, client, user, second_user, track, dj_user, tmp_path):
        """First buyer triggers fetch+upload; second buyer streams from R2 with zero Drive hits."""
        from apps.commerce.models import Purchase
        from apps.downloads import external_cache

        _, dj = dj_user
        track.is_external_link = True
        track.source_url = "https://drive.google.com/file/d/SHARED1234567890/view"
        track.source_type = "gdrive"
        track.save()
        for u in (user, second_user):
            Purchase.objects.create(
                user=u.profile,
                content_id=track.id,
                content_type="track",
                original_price=track.price,
                price_paid=track.price,
                seller=dj,
                status="paid",
            )
        cached = tmp_path / "shared.mp3"
        cached.write_bytes(b"SHARED" * 200)
        fake_key = external_cache.cache_key_for(track.id, track.source_url)

        class FakeBody:
            def __init__(self, data):
                self._data = data

            def __iter__(self):
                yield self._data

        calls = {"fetch": 0}

        def fake_fetch(url, stype, dest):
            calls["fetch"] += 1
            return str(cached)

        # Buyer 1: cold cache -> fetch once, upload to R2.
        client.force_login(user)
        r1 = client.post(
            "/api/v1/downloads/external/issue/",
            {"content_type": "track", "content_id": track.id},
            content_type="application/json",
        )
        t1 = r1.json()["token"]
        with (
            patch("apps.downloads.external_views.fetch_from_source", side_effect=fake_fetch),
            patch.object(external_cache, "is_configured", return_value=True),
            patch.object(external_cache, "get_fresh_key", return_value=None),
            patch.object(external_cache, "upload_file", return_value=f"r2://bkt/{fake_key}") as up,
            patch.object(external_cache, "stream_ref", return_value=(FakeBody(b"SHARED" * 200), 1200, "audio/mpeg")),
        ):
            d1 = client.get(f"/api/v1/downloads/external/{t1}/")
            assert d1.status_code == 200
            assert calls["fetch"] == 1
            assert up.called

        # Buyer 2: warm cache -> NO fetch at all.
        c2 = Client()
        c2.force_login(second_user)
        r2 = c2.post(
            "/api/v1/downloads/external/issue/",
            {"content_type": "track", "content_id": track.id},
            content_type="application/json",
        )
        t2 = r2.json()["token"]
        with (
            patch("apps.downloads.external_views.fetch_from_source", side_effect=fake_fetch),
            patch.object(external_cache, "is_configured", return_value=True),
            patch.object(external_cache, "get_fresh_key", return_value=fake_key),
            patch.object(external_cache, "_bucket", return_value="bkt"),
            patch.object(external_cache, "stream_ref", return_value=(FakeBody(b"SHARED" * 200), 1200, "audio/mpeg")),
        ):
            d2 = c2.get(f"/api/v1/downloads/external/{t2}/")
            assert d2.status_code == 200
            assert calls["fetch"] == 1  # still 1 — second buyer reused R2, no Drive hit
