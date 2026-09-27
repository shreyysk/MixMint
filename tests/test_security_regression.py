"""Security regression tests: XSS, SSRF, traversal, money exactness, field leaks."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError


@pytest.mark.django_db
class TestEmbedXSS:
    def test_quote_breakout_escaped(self, dj_user):
        """A URL carrying an attribute break-out is not a valid video id -> no iframe at all."""
        from apps.tracks.models import Track
        from apps.tracks.frontend_views import _build_preview_embeds

        _, dj = dj_user
        track = Track(
            dj=dj,
            title="X",
            price=Decimal("50.00"),
            file_key="x.wav",
            preview_type="youtube",
            youtube_url='https://www.youtube.com/embed/abc"onload="alert(1)',
        )
        assert _build_preview_embeds(track) == []

        track.youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10"
        embeds = _build_preview_embeds(track)
        assert embeds, "benign embed must still render"
        html = str(embeds[0][2])
        assert "youtube-nocookie.com/embed/dQw4w9WgXcQ" in html
        assert "onload" not in html

    def test_foreign_hosts_are_never_framed(self, dj_user):
        from apps.tracks.models import Track
        from apps.tracks.frontend_views import _build_preview_embeds

        _, dj = dj_user
        track = Track(
            dj=dj,
            title="X",
            price=Decimal("50.00"),
            file_key="x.wav",
            youtube_url="https://evil.example/watch?v=dQw4w9WgXcQ",
        )
        assert _build_preview_embeds(track) == []

    def test_javascript_scheme_rejected(self, dj_user):
        from apps.tracks.models import Track
        from apps.tracks.frontend_views import _build_preview_embeds

        _, dj = dj_user
        track = Track(
            dj=dj,
            title="X",
            price=Decimal("50.00"),
            file_key="x.wav",
            instagram_url="javascript:alert(1)",
        )
        assert _build_preview_embeds(track) == []

    def test_album_embeds_escaped(self, dj_user):
        from apps.albums.models import AlbumPack
        from apps.albums import frontend_views as album_views

        _, dj = dj_user
        album = AlbumPack(
            dj=dj,
            title="A",
            price=Decimal("499.00"),
            file_key="a.zip",
            preview_type="youtube",
            youtube_url='https://youtube.com/watch?v=x"><script>alert(1)</script>',
        )
        from apps.core.embeds import build_preview_embeds

        assert album_views is not None
        assert build_preview_embeds(album) == []  # injected markup never becomes an iframe


class TestSSRFGuard:
    def test_blocks_private_and_metadata(self):
        from apps.downloads.source_fetch import assert_public_url

        for bad in [
            "http://169.254.169.254/latest/meta-data/",
            "http://127.0.0.1:8000/admin/",
            "http://localhost:3000/x",
            "http://10.0.0.5/secret",
            "http://192.168.1.1/",
            "http://[::1]/",
            "ftp://8.8.8.8/x",
            "http://metadata.google.internal/",
            "gopher://8.8.8.8/x",
        ]:
            with pytest.raises(ValueError):
                assert_public_url(bad)

    def test_allows_public_ip_literal(self):
        from apps.downloads.source_fetch import assert_public_url

        assert assert_public_url("https://8.8.8.8/file.mp3") is True

    def test_probe_rejects_blocked_host(self):
        from apps.downloads.source_fetch import probe_source

        ok, info = probe_source("http://169.254.169.254/latest/meta-data/")
        assert ok is False
        assert "blocked" in info.lower()


@pytest.mark.django_db
class TestFieldLeaks:
    def test_track_private_fields_hidden(self, client, track):
        data = client.get(f"/api/v1/tracks/{track.id}/").json()
        for field in ("file_key", "source_url", "source_type", "external_link_url", "external_link_provider"):
            assert field not in data, field

    def test_album_private_fields_hidden(self, client, album):
        data = client.get(f"/api/v1/albums/{album.id}/").json()
        for field in ("file_key", "original_file_key", "external_link_url", "external_link_provider"):
            assert field not in data, field

    def test_file_key_traversal_rejected(self):
        from apps.tracks.serializers import TrackSerializer

        s = TrackSerializer()
        from rest_framework.exceptions import ValidationError as DRFValidationError

        for bad in ("../../etc/passwd.mp3", "/abs/path.mp3", "C:\\win.mp3", "a\x00.mp3"):
            with pytest.raises(DRFValidationError):
                s.validate_file_key(bad)
        assert s.validate_file_key("tracks/song.wav") == "tracks/song.wav"


@pytest.mark.django_db
class TestMoneyExactness:
    def test_redownload_rounds_half_up_not_truncates(self):
        from types import SimpleNamespace
        from apps.payments.views import calculate_total_price_paise

        content = SimpleNamespace(price=Decimal("19.99"))
        # 19.99 * 0.5 = 9.995 -> HALF_UP 10.00 -> 1000 paise (float code gave 999)
        assert calculate_total_price_paise(content, is_redownload=True) == 1000

    def test_full_price_exact_paise(self):
        from types import SimpleNamespace
        from apps.payments.views import calculate_total_price_paise

        assert calculate_total_price_paise(SimpleNamespace(price=Decimal("19.99"))) == 1999
        assert calculate_total_price_paise(SimpleNamespace(price=Decimal("100.00"))) == 10000

    def test_cart_discount_deterministic(self, user, track, dj_user):
        from apps.commerce.models import Cart, CartItem

        cart = Cart.objects.create(user=user.profile)
        for i in range(3):
            CartItem.objects.create(cart=cart, content_type="track", content_id=track.id + i, price=10000)
        cart.refresh_from_db()
        assert cart.discount_percentage == 5
        assert cart.discount_amount == 1500  # 5% of 30000, exact
        assert cart.final_total == 28500
