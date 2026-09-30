"""Run: python -m pytest vault_worker/test_app.py  (needs fastapi, httpx, moto)."""

import importlib
import os
import time
from unittest import mock

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from moto import mock_aws  # noqa: E402


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("VAULT_WORKER_SECRET", "s3cret")
    monkeypatch.setenv("BOT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("WORK_DIR", str(tmp_path / "tmp"))
    monkeypatch.setenv("R2_ENDPOINT", "https://acct.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "x")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "y")
    with mock_aws():
        import boto3

        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="raw")
        import vault_worker.app as app_mod

        app_mod = importlib.reload(app_mod)
        monkeypatch.setattr(app_mod, "r2", lambda: s3)
        yield app_mod, s3, tmp_path


class FakeBotAPI:
    """Local Bot API Server stand-in: reads file:// paths, stores them, getFile returns an absolute path."""

    def __init__(self, root):
        self.root, self.sent, self.callbacks = root, [], []

    def post(self, url, data=None, json=None, timeout=None, headers=None):
        r = mock.Mock(status_code=200)
        if "/sendDocument" in url:
            path = data["document"][len("file://"):]
            with open(path, "rb") as fh:
                content = fh.read()
            stored = self.root / "documents" / "file_1.bin"
            stored.parent.mkdir(exist_ok=True)
            stored.write_bytes(content)
            self.sent.append((data, os.path.basename(path)))
            r.json.return_value = {"ok": True, "result": {"message_id": 7, "document": {"file_id": "FID", "file_unique_id": "U", "file_size": len(content)}}}
        elif "/getFile" in url:
            r.json.return_value = {"ok": True, "result": {"file_id": "FID", "file_path": str(self.root / "documents" / "file_1.bin")}}
        elif "/getMe" in url:
            r.json.return_value = {"ok": True, "result": {"id": 1}}
        else:  # callback to MixMint
            self.callbacks.append(json)
        return r


def _wait(client, job_id):
    for _ in range(100):
        s = client.get(f"/jobs/{job_id}", headers={"Authorization": "Bearer s3cret"}).json()
        if s["status"] in ("done", "failed"):
            return s
        time.sleep(0.05)
    raise AssertionError("job never finished")


def test_archive_then_restore_round_trip(env):
    app_mod, s3, root = env
    fake = FakeBotAPI(root)
    s3.put_object(Bucket="raw", Key="albums/1/pack.zip", Body=b"Z" * 5000)
    with mock.patch.object(app_mod.requests, "post", fake.post):
        c = TestClient(app_mod.app)
        H = {"Authorization": "Bearer s3cret"}
        job = c.post("/jobs", headers=H, json={"action": "archive", "key": "albums/1/pack.zip", "bucket": "raw", "chat_id": "-100",
                                               "filename": "DJ X - Pack.zip", "caption": "#A1", "callback": "https://site/vault/callback/",
                                               "kind": "album", "content_id": 1}).json()
        s = _wait(c, job["job_id"])
        assert s["ok"] and s["result"]["file_id"] == "FID"
        assert fake.sent[0][1] == "DJ X - Pack.zip"
        assert fake.callbacks[-1]["file_id"] == "FID" and fake.callbacks[-1]["ok"] is True
        assert not os.listdir(root / "tmp")  # temp copy cleaned up

        s3.delete_object(Bucket="raw", Key="albums/1/pack.zip")
        job = c.post("/jobs", headers=H, json={"action": "restore", "key": "albums/1/pack.zip", "bucket": "raw", "file_id": "FID",
                                               "callback": "https://site/vault/callback/", "kind": "album", "content_id": 1}).json()
        s = _wait(c, job["job_id"])
        assert s["ok"], s
        assert s3.get_object(Bucket="raw", Key="albums/1/pack.zip")["Body"].read() == b"Z" * 5000


def test_needs_secret(env):
    app_mod, *_ = env
    c = TestClient(app_mod.app)
    assert c.post("/jobs", json={"action": "restore"}).status_code == 403
    assert c.post("/jobs", headers={"Authorization": "Bearer wrong"}, json={}).status_code == 403


def test_bot_proxy_blocks_local_paths_and_wrong_token(env):
    app_mod, *_ = env
    c = TestClient(app_mod.app)
    assert c.post("/bot999:zzz/sendMessage", json={"chat_id": 1, "text": "hi"}).status_code == 401
    assert c.post("/bot123:abc/sendDocument", json={"chat_id": 1, "document": "file:///etc/passwd"}).status_code == 400
    assert c.post("/bot123:abc/sendDocument", data={"chat_id": "1", "document": "file:///etc/passwd"}).status_code == 400
    assert c.post("/bot123:abc/logOut", json={}).status_code == 403
    with mock.patch.object(app_mod.requests, "request") as req:
        req.return_value = mock.Mock(status_code=200, content=b'{"ok":true,"result":{}}', headers={"content-type": "application/json"})
        r = c.post("/bot123:abc/sendMessage", json={"chat_id": 1, "text": "my file: is broken"})
        assert r.status_code == 200 and req.called
