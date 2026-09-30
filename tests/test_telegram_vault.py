"""Telegram vault: uploads are copied to private channels; R2 stays the download source and is
restored from the channel copy if an object goes missing."""

import json
from decimal import Decimal
from unittest import mock

import boto3
import pytest
from django.test import Client, override_settings
from moto import mock_aws

R2 = dict(AWS_ACCESS_KEY_ID="test", AWS_SECRET_ACCESS_KEY="test", AWS_S3_ENDPOINT_URL="https://acct.r2.cloudflarestorage.com",
          R2_PRIVATE_BUCKET="raw", R2_PUBLIC_BUCKET="pub", R2_PUBLIC_URL="https://cdn.example.com",
          TELEGRAM_BOT_TOKEN="123:abc", TELEGRAM_ADMIN_CHAT_ID="999")


class FakeTG:
    """Stands in for api.telegram.org."""

    def __init__(self):
        self.calls, self.files = [], {}

    def post(self, url, data=None, files=None, json=None, timeout=None):
        method = url.rsplit("/", 1)[-1]
        payload = data or json or {}
        self.calls.append((method, payload, files))
        r = mock.Mock()
        if method == "sendDocument":
            name, body = files["document"]
            content = body.read()
            self.files["F1"] = content
            r.json.return_value = {"ok": True, "result": {"message_id": 55, "document": {"file_id": "F1", "file_unique_id": "U1", "file_name": name}}}
        elif method == "getFile":
            r.json.return_value = {"ok": True, "result": {"file_path": "documents/f1.wav"}}
        else:
            r.json.return_value = {"ok": True, "result": {"message_id": 56}}
        return r

    def get(self, url, timeout=None):
        r = mock.Mock()
        r.content = self.files["F1"]
        r.raise_for_status = lambda: None
        return r


@pytest.fixture
def env(db):
    with mock_aws(), override_settings(**R2):
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="raw")
        s3.create_bucket(Bucket="pub")
        tg = FakeTG()
        with mock.patch("apps.core.r2.client", lambda: s3), \
             mock.patch("apps.admin_panel.vault.requests", tg), mock.patch("apps.admin_panel.support.requests", tg):
            yield s3, tg


def _link(kind="singles", code=None):
    from apps.admin_panel import vault
    from apps.admin_panel.support import handle_update

    handle_update({"channel_post": {"chat": {"id": -100111 if kind == "singles" else -100222, "type": "channel", "title": f"MM {kind}"},
                                    "text": f"/link {kind} {code or vault.link_code()}"}})


def _track(dj, s3, size=1000, title="Vault Song"):
    from apps.tracks.models import Track

    key = f"tracks/{dj.id}/song.wav"
    s3.put_object(Bucket="raw", Key=key, Body=b"R" * size)
    return Track.objects.create(dj=dj, title=title, price=Decimal("99"), file_key=key, file_size=size,
                                preview_type="youtube", youtube_url="https://youtube.com/watch?v=abc")


def test_link_needs_the_code(env):
    from apps.admin_panel.models import PlatformSettings

    _link("singles", code="wrong")
    assert PlatformSettings.load().tg_singles_channel_id == ""
    _link("singles")
    _link("zips")
    ps = PlatformSettings.load()
    assert ps.tg_singles_channel_id == "-100111" and ps.tg_zips_channel_id == "-100222"


def test_archive_posts_file_to_singles_channel(env, dj_user):
    from apps.admin_panel import vault
    from apps.admin_panel.models import VaultFile

    s3, tg = env
    _link("singles")
    t = _track(dj_user[1], s3)
    rec = vault.archive("track", t)
    assert rec.status == "archived" and rec.file_id == "F1" and rec.message_id == 55
    method, data, files = [c for c in tg.calls if c[0] == "sendDocument"][0]
    assert data["chat_id"] == "-100111" and f"#T{t.id}" in data["caption"]
    assert tg.files["F1"] == b"R" * 1000
    assert VaultFile.objects.count() == 1
    vault.archive("track", t)  # idempotent
    assert len([c for c in tg.calls if c[0] == "sendDocument"]) == 1


def test_big_file_gets_a_note_not_an_upload(env, dj_user):
    from apps.admin_panel import vault

    s3, tg = env
    _link("singles")
    t = _track(dj_user[1], s3)
    t.file_size = 300 * 1024 * 1024
    rec = vault.archive("track", t)
    assert rec.status == "too_large"
    assert not [c for c in tg.calls if c[0] == "sendDocument"]
    note = [c for c in tg.calls if c[0] == "sendMessage" and c[1].get("chat_id") == "-100111"][-1]
    assert "R2 only" in note[1]["text"]


def test_no_channel_means_no_vault(env, dj_user):
    from apps.admin_panel import vault

    s3, tg = env
    assert vault.archive("track", _track(dj_user[1], s3)) is None


def test_missing_r2_object_is_restored_from_channel(env, dj_user):
    from apps.admin_panel import vault

    s3, tg = env
    _link("singles")
    t = _track(dj_user[1], s3)
    vault.archive("track", t)
    s3.delete_object(Bucket="raw", Key=t.file_key)
    assert vault.restore("track", t) == "ready"
    assert s3.get_object(Bucket="raw", Key=t.file_key)["Body"].read() == b"R" * 1000


def test_sweep_backfills(env, dj_user):
    from apps.admin_panel import vault

    s3, tg = env
    _track(dj_user[1], s3, title="Old one")
    _link("singles")
    assert vault.sweep()["archived"] == 1
    assert vault.sweep()["archived"] == 0


def test_admin_support_page_shows_link_code(env, admin_user):
    from apps.admin_panel import vault

    c = Client()
    c.force_login(admin_user)
    with mock.patch("apps.admin_panel.support.webhook_info", return_value={}):
        html = c.get("/api/v1/admin/support/").content.decode()
    assert f"/link singles {vault.link_code()}" in html


def test_external_link_conversion_is_retired(dj_user, track):
    c = Client()
    c.force_login(dj_user[0])
    r = c.post(f"/api/v1/tracks/{track.id}/convert-external/", json.dumps({"external_link_url": "https://drive.google.com/x"}),
               content_type="application/json")
    assert r.status_code == 410


# ───────────────── R2 as a holding area, Telegram as the permanent store ─────────────────
from datetime import timedelta  # noqa: E402

from django.utils import timezone  # noqa: E402


def _archived(env, dj, **kw):
    from apps.admin_panel import vault

    s3, tg = env
    _link("singles")
    t = _track(dj, s3, **kw)
    rec = vault.archive("track", t)
    assert rec.status == "archived"
    return t, rec


def test_hold_is_10_days_from_upload_then_r2_is_freed(env, dj_user):
    from apps.admin_panel import vault

    s3, tg = env
    t, rec = _archived(env, dj_user[1])
    assert abs((rec.r2_hold_until - t.created_at) - timedelta(days=10)) < timedelta(seconds=5)
    assert vault.evict() == 0  # day 0: still held
    assert vault.evict(now=timezone.now() + timedelta(days=11)) == 1
    rec.refresh_from_db()
    assert rec.r2_present is False
    assert s3.list_objects_v2(Bucket="raw").get("KeyCount", 0) == 0


def test_limited_drop_stays_in_r2_until_sold_out(env, dj_user, user):
    from apps.admin_panel import vault
    from apps.commerce.models import Purchase

    s3, tg = env
    t, rec = _archived(env, dj_user[1], title="Drop")
    t.copies_limit = 1
    t.save()
    later = timezone.now() + timedelta(days=30)
    assert vault.evict(now=later) == 0
    Purchase.objects.create(user=user.profile, content_type="track", content_id=t.id, seller=t.dj, original_price=t.price,
                            price_paid=t.price, status="paid", gateway_order_id="MM_SOLD")
    assert vault.evict(now=later) == 1


def test_evicted_file_is_fetched_back_before_download_link(env, dj_user, user):
    from apps.admin_panel.models import VaultFile
    from apps.commerce.models import Purchase

    s3, tg = env
    t, rec = _archived(env, dj_user[1])
    from apps.admin_panel import vault

    vault.evict(now=timezone.now() + timedelta(days=11))
    Purchase.objects.create(user=user.profile, content_type="track", content_id=t.id, seller=t.dj, original_price=t.price,
                            price_paid=t.price, status="paid", gateway_order_id="MM_B")
    c = Client()
    c.force_login(user)
    r = c.post(f"/api/v1/tracks/{t.id}/download-token/", {}, content_type="application/json")
    assert r.status_code == 200 and "download_url" in r.json()  # no worker: ≤20 MB restored inline
    rec = VaultFile.objects.get(pk=rec.pk)
    assert rec.r2_present and rec.restored_count == 1
    assert rec.r2_hold_until > timezone.now() + timedelta(days=2)


def test_worker_mode_archive_and_restore_via_callbacks(env, dj_user, user, settings):
    from apps.admin_panel import vault
    from apps.admin_panel.models import VaultFile
    from apps.commerce.models import Purchase

    s3, tg = env
    settings.VAULT_WORKER_URL, settings.VAULT_WORKER_SECRET = "https://vault.example", "wsecret"
    jobs = []

    def worker_post(url, json=None, timeout=None, headers=None, data=None, files=None):
        if url.startswith("https://vault.example"):
            jobs.append(json)
            return mock.Mock(status_code=200, json=lambda: {"job_id": f"J{len(jobs)}"})
        return tg.post(url, data=data, files=files, json=json, timeout=timeout)

    tg.post_orig = tg.post
    with mock.patch.object(tg, "post", worker_post):
        _link("singles")
        t = _track(dj_user[1], s3, size=300 * 1024 * 1024 // 1000)  # size field only matters for limits
        t.file_size = 300 * 1024 * 1024
        t.save()
        rec = vault.archive("track", t)
        assert rec.status == "pending" and jobs[-1]["action"] == "archive" and jobs[-1]["chat_id"] == "-100111"

        c = Client()
        bad = c.post("/vault/callback/", json.dumps({}), content_type="application/json", HTTP_AUTHORIZATION="Bearer nope")
        assert bad.status_code == 403
        cb = dict(action="archive", kind="track", content_id=t.id, key=t.file_key, ok=True, message_id=9, file_id="BIG", file_unique_id="u")
        assert c.post("/vault/callback/", json.dumps(cb), content_type="application/json", HTTP_AUTHORIZATION="Bearer wsecret").json()["ok"]
        rec.refresh_from_db()
        assert rec.status == "archived" and rec.file_id == "BIG"

        assert vault.evict(now=timezone.now() + timedelta(days=11)) == 1  # 300 MB is restorable with the worker
        Purchase.objects.create(user=user.profile, content_type="track", content_id=t.id, seller=t.dj, original_price=t.price,
                                price_paid=t.price, status="paid", gateway_order_id="MM_W")
        buyer = Client()
        buyer.force_login(user)
        r = buyer.post(f"/api/v1/tracks/{t.id}/download-token/", {}, content_type="application/json")
        assert r.status_code == 202 and r.json()["preparing"]
        assert jobs[-1]["action"] == "restore" and jobs[-1]["file_id"] == "BIG"
        n = len(jobs)
        assert buyer.post(f"/api/v1/tracks/{t.id}/download-token/", {}, content_type="application/json").status_code == 202
        assert len(jobs) == n  # no duplicate restore job

        s3.put_object(Bucket="raw", Key=t.file_key, Body=b"x")  # the worker put it back
        cb = dict(action="restore", kind="track", content_id=t.id, key=t.file_key, ok=True)
        c.post("/vault/callback/", json.dumps(cb), content_type="application/json", HTTP_AUTHORIZATION="Bearer wsecret")
        assert VaultFile.objects.get(pk=rec.pk).r2_present
        r = buyer.post(f"/api/v1/tracks/{t.id}/download-token/", {}, content_type="application/json")
        assert r.status_code == 200 and "download_url" in r.json()


def test_not_evicted_when_it_cannot_come_back(env, dj_user):
    from apps.admin_panel import vault

    s3, tg = env
    t, rec = _archived(env, dj_user[1])
    rec.size = 100 * 1024 * 1024  # over 20 MB and no worker → keep in R2
    rec.save()
    assert vault.evict(now=timezone.now() + timedelta(days=11)) == 0


def test_admin_can_change_hold(env, admin_user):
    from apps.admin_panel.models import PlatformSettings

    c = Client()
    c.force_login(admin_user)
    with mock.patch("apps.admin_panel.support.webhook_info", return_value={}):
        c.post("/api/v1/admin/support/", {"action": "vault_settings", "hold_days": "14", "rehold_days": "5", "evict": "on"})
    ps = PlatformSettings.load()
    assert ps.vault_hold_days == 14 and ps.vault_rehold_days == 5 and ps.vault_evict_enabled
