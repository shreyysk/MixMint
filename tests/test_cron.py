"""Secured cron endpoints (/cron/<job>/) for worker-free hosting."""

import pytest


@pytest.mark.django_db
class TestCronEndpoints:
    def test_wrong_secret_rejected(self, client):
        resp = client.get("/cron/cleanup/?secret=nope")
        assert resp.status_code == 403

    def test_missing_secret_rejected(self, client):
        assert client.get("/cron/cleanup/").status_code == 403

    def test_unknown_job_404(self, client, settings):
        settings.CRON_SECRET = "s3cr3t"
        resp = client.get("/cron/nope/?secret=s3cr3t")
        assert resp.status_code == 404
        assert "cleanup" in resp.json()["jobs"]

    def test_cleanup_runs(self, client, settings):
        settings.CRON_SECRET = "s3cr3t"
        resp = client.get("/cron/cleanup/?secret=s3cr3t")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True and body["ran"] == ["cleanup_tokens"]

    def test_warm_cache_registered(self, client, settings):
        settings.CRON_SECRET = "s3cr3t"
        resp = client.get("/cron/warm-cache/?secret=s3cr3t")
        assert resp.status_code == 200
        assert resp.json()["ran"] == ["warm_external_cache"]

    def test_vercel_config_valid(self):
        import json
        from pathlib import Path

        cfg = json.loads(Path("vercel.json").read_text())
        assert cfg["functions"]["config/wsgi.py"]["maxDuration"] <= 300

    def test_warm_command_skips_big_and_bounds_batch(self, dj_user, tmp_path):
        from decimal import Decimal
        from unittest.mock import patch
        from django.core.management import call_command
        from apps.tracks.models import Track

        _, dj = dj_user
        for i in range(5):
            Track.objects.create(
                dj=dj,
                title=f"Warm {i}",
                price=Decimal("50.00"),
                file_key="",
                preview_type="youtube",
                youtube_url="https://youtube.com/watch?v=x",
                is_external_link=True,
                source_url=f"https://drive.google.com/file/d/WARM{i}/view",
                source_type="gdrive",
            )
        small = tmp_path / "s.mp3"
        small.write_bytes(b"x" * 100)
        calls = {"fetch": 0, "upload": 0}

        def fake_fetch(url, stype, dest):
            calls["fetch"] += 1
            clone = tmp_path / f"clone{calls['fetch']}.mp3"
            clone.write_bytes(b"x" * 100)
            return str(clone)

        def fake_upload(local, tid, url):
            calls["upload"] += 1
            return f"r2://bkt/k{tid}"

        with (
            patch("apps.downloads.external_cache.is_configured", return_value=True),
            patch("apps.downloads.external_cache.get_fresh_key", return_value=None),
            patch("apps.downloads.source_fetch.probe_source", return_value=(True, "OK")),
            patch("apps.downloads.source_fetch.fetch_from_source", side_effect=fake_fetch),
            patch("apps.downloads.external_cache.upload_file", side_effect=fake_upload),
        ):
            call_command("warm_external_cache")
        assert calls["fetch"] == 3  # bounded batch
        assert calls["upload"] == 3
