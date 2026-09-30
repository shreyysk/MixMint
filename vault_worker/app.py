"""
MixMint vault worker: moves files between Cloudflare R2 and the private Telegram channels through
a Local Bot API Server (no 50 MB / 20 MB limits: up to 2 GB per file).

Runs next to the `telegram-bot-api` container (see docker-compose.yml). MixMint (on Vercel) talks
only to this service:

    POST /jobs            {"action": "archive", key, bucket, chat_id, caption, filename, callback, kind, content_id}
                          {"action": "restore", key, bucket, file_id, callback, kind, content_id}
    GET  /jobs/<id>       job status
    GET  /health          bot + R2 check
    ANY  /bot<token>/<m>  safe proxy to the Bot API for the site's normal bot calls (help desk,
                          webhook set-up). Local file paths are refused, so a leaked token can't
                          read files from this server.

Every call needs `Authorization: Bearer <VAULT_WORKER_SECRET>` except the /bot proxy (which needs
the real bot token, like Telegram itself). Finished jobs are reported to the `callback` URL with
the same bearer secret.
"""

import hmac
import re
import logging
import os
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import boto3
import requests
from botocore.config import Config
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response

log = logging.getLogger("vault")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
SECRET = os.environ.get("VAULT_WORKER_SECRET", "")
BOT_API = os.environ.get("BOT_API_URL", "http://bot-api:8081").rstrip("/")
WORK_DIR = os.environ.get("WORK_DIR", "/var/lib/telegram-bot-api/mixmint-tmp")
DATA_DIR = os.environ.get("BOT_DATA_DIR", "/var/lib/telegram-bot-api")
KEEP_CACHE = os.environ.get("KEEP_BOT_CACHE", "") == "1"
ALLOWED_PROXY = {
    "getMe", "sendMessage", "setWebhook", "deleteWebhook", "getWebhookInfo", "setMyCommands",
    "sendDocument", "getFile", "getChat", "editMessageText", "deleteMessage",
}

app = FastAPI(title="MixMint vault worker", docs_url=None, redoc_url=None)
pool = ThreadPoolExecutor(max_workers=int(os.environ.get("WORKERS", "2")))
JOBS = {}
_lock = threading.Lock()


def r2():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("R2_ENDPOINT"),
        aws_access_key_id=os.environ.get("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
        config=Config(signature_version="s3v4", retries={"max_attempts": 5, "mode": "standard"}),
    )


def _auth(request):
    auth = request.headers.get("authorization", "")
    given = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    if not SECRET or not hmac.compare_digest(given, SECRET):
        raise HTTPException(status_code=403, detail="forbidden")


def bot(method, data, timeout=60):
    r = requests.post(f"{BOT_API}/bot{TOKEN}/{method}", data=data, timeout=timeout)
    body = r.json()
    if not body.get("ok"):
        raise RuntimeError(str(body.get("description") or f"{method} failed")[:200])
    return body["result"]


def _safe_name(name):
    name = "".join(c if c.isalnum() or c in " -_().," else "_" for c in (name or "file"))
    return name.strip(" .")[:120] or "file"


# ─────────────────────────────── jobs ───────────────────────────────
def do_archive(job):
    """R2 → local disk → Local Bot API (by path, up to 2 GB) → channel post."""
    folder = os.path.join(WORK_DIR, job["id"])
    os.makedirs(folder, exist_ok=True)
    os.chmod(folder, 0o755)
    path = os.path.join(folder, _safe_name(job["filename"]))
    try:
        r2().download_file(job["bucket"], job["key"], path)
        os.chmod(path, 0o644)  # the bot-api container runs as another user
        msg = bot("sendDocument", {
            "chat_id": job["chat_id"], "caption": job.get("caption", "")[:1000],
            "document": f"file://{path}", "disable_notification": "true",
            "disable_content_type_detection": "true",
        }, timeout=3600)
        doc = msg.get("document") or msg.get("audio") or {}
        if not doc.get("file_id"):
            raise RuntimeError("Telegram returned no file")
        return {"message_id": msg.get("message_id"), "file_id": doc["file_id"],
                "file_unique_id": doc.get("file_unique_id", ""), "size": doc.get("file_size")}
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def do_restore(job):
    """Channel copy → Local Bot API downloads it to disk (no size limit) → multipart upload to R2."""
    info = bot("getFile", {"file_id": job["file_id"]}, timeout=3600)
    path = info.get("file_path") or ""
    tmp = None
    if not os.path.isabs(path):  # not in --local mode: fall back to the HTTP file endpoint
        tmp = os.path.join(WORK_DIR, job["id"] + ".bin")
        os.makedirs(WORK_DIR, exist_ok=True)
        with requests.get(f"{BOT_API}/file/bot{TOKEN}/{path}", stream=True, timeout=3600) as resp:
            resp.raise_for_status()
            with open(tmp, "wb") as fh:
                shutil.copyfileobj(resp.raw, fh, 1024 * 1024)
        path = tmp
    if not os.path.realpath(path).startswith(os.path.realpath(DATA_DIR)):
        raise RuntimeError("Unexpected file location")
    try:
        r2().upload_file(path, job["bucket"], job["key"])
        return {"size": os.path.getsize(path)}
    finally:
        if tmp or not KEEP_CACHE:
            try:
                os.remove(path)
            except OSError:
                pass


def _report(job):
    if not job.get("callback"):
        return
    payload = {k: job.get(k) for k in ("id", "action", "kind", "content_id", "key", "ok", "error")}
    payload.update(job.get("result") or {})
    for attempt in range(5):
        try:
            r = requests.post(job["callback"], json=payload, timeout=20, headers={"Authorization": f"Bearer {SECRET}"})
            if r.status_code < 500:
                return
        except Exception as exc:  # noqa: BLE001
            log.warning("callback failed (%s), retrying", type(exc).__name__)
        time.sleep(2 ** attempt)


def run(job):
    job["status"], job["started"] = "running", time.time()
    try:
        job["result"] = do_archive(job) if job["action"] == "archive" else do_restore(job)
        job["ok"], job["status"] = True, "done"
        log.info("%s %s %s ok", job["action"], job.get("kind"), job.get("content_id"))
    except Exception as exc:  # noqa: BLE001
        job["ok"], job["status"], job["error"] = False, "failed", str(exc)[:250]
        log.error("%s %s %s failed: %s", job["action"], job.get("kind"), job.get("content_id"), job["error"])
    job["finished"] = time.time()
    _report(job)
    with _lock:  # keep the last 500 jobs
        for old in sorted(JOBS, key=lambda k: JOBS[k].get("created", 0))[:-500]:
            JOBS.pop(old, None)


@app.post("/jobs")
async def create_job(request: Request):
    _auth(request)
    data = await request.json()
    action = data.get("action")
    need = {"archive": ("key", "bucket", "chat_id", "filename"), "restore": ("key", "bucket", "file_id")}.get(action)
    if not need or any(not data.get(k) for k in need):
        raise HTTPException(status_code=400, detail="bad job")
    job = {**data, "id": uuid.uuid4().hex, "status": "queued", "created": time.time()}
    with _lock:
        JOBS[job["id"]] = job
    pool.submit(run, job)
    return {"job_id": job["id"], "status": "queued"}


@app.get("/jobs/{job_id}")
def job_status(job_id: str, request: Request):
    _auth(request)
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="unknown job")
    return {k: job.get(k) for k in ("id", "action", "status", "ok", "error", "result", "content_id", "kind")}


@app.get("/health")
def health(request: Request):
    _auth(request)
    out = {"bot": False, "r2": False, "queued": sum(1 for j in JOBS.values() if j["status"] in ("queued", "running"))}
    try:
        out["bot"] = bool(bot("getMe", {}, timeout=10).get("id"))
    except Exception as exc:  # noqa: BLE001
        out["bot_error"] = str(exc)[:120]
    try:
        r2().list_buckets()
        out["r2"] = True
    except Exception as exc:  # noqa: BLE001
        out["r2_error"] = type(exc).__name__
    return out


@app.api_route("/bot{token}/{method}", methods=["GET", "POST"])
async def bot_proxy(token: str, method: str, request: Request):
    """The site's ordinary bot calls, forwarded to the Local Bot API Server with guard rails."""
    if not TOKEN or not hmac.compare_digest(token, TOKEN):
        return JSONResponse({"ok": False, "error_code": 401, "description": "Unauthorized"}, status_code=401)
    if method not in ALLOWED_PROXY:
        return JSONResponse({"ok": False, "error_code": 403, "description": "Method not allowed here"}, status_code=403)
    body = await request.body()
    from urllib.parse import unquote_to_bytes

    probe = (unquote_to_bytes(body) + b" " + unquote_to_bytes(request.url.query or "")).lower()
    if re.search(rb'(?:^|["=&\n])\s*file:/', probe):  # a field whose value is a local path
        return JSONResponse({"ok": False, "error_code": 400, "description": "Local paths are not allowed"}, status_code=400)
    headers = {k: v for k, v in request.headers.items() if k.lower() in ("content-type",)}
    r = requests.request(request.method, f"{BOT_API}/bot{TOKEN}/{method}", params=dict(request.query_params),
                         data=body, headers=headers, timeout=120)
    if method == "getFile":  # never reveal where files sit on this server
        try:
            data = r.json()
            if data.get("ok") and os.path.isabs(data["result"].get("file_path", "")):
                data["result"].pop("file_path", None)
            return JSONResponse(data, status_code=r.status_code)
        except Exception:  # noqa: BLE001
            pass
    return Response(r.content, status_code=r.status_code, media_type=r.headers.get("content-type", "application/json"))
