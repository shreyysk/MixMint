"""
Telegram vault over MTProto, run inside MixMint itself (no extra server).

The public Bot API is HTTP and caps bots at 50 MB up / 20 MB down. Telegram's native protocol
(MTProto, here through Telethon) lets the same bot send and fetch files up to 2 GB, and it runs
fine inside a Vercel function. Needs TELEGRAM_API_ID / TELEGRAM_API_HASH from my.telegram.org.

How a job runs:
  * vault.archive()/restore() call `trigger()`, which fires a signed POST at /vault/run/ and
    doesn't wait: that second request runs the transfer (up to the function's 300 s).
  * One transfer at a time (a cache lock): the bot's MTProto session must never be used from two
    places at once, or Telegram revokes it (AUTH_KEY_DUPLICATED).
  * The login is saved (StringSession in PlatformSettings) so each run reuses it instead of
    logging the bot in again (Telegram rate-limits bot logins).
"""

import asyncio
import hashlib
import hmac
import logging
import time

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("mixmint")
LOCK_KEY = "vault_mtproto_lock"
LOCK_SECONDS = 320
PART = 8 * 1024 * 1024  # R2 multipart part size when restoring


def configured():
    from . import support

    return bool(getattr(settings, "TELEGRAM_API_ID", "") and getattr(settings, "TELEGRAM_API_HASH", "") and support._token())


def run_secret():
    return hashlib.sha256(f"vault-run:{settings.SECRET_KEY}".encode()).hexdigest()[:48]


def sign(payload):
    msg = f"{payload.get('action')}:{payload.get('kind')}:{payload.get('content_id')}"
    return hmac.new(run_secret().encode(), msg.encode(), hashlib.sha256).hexdigest()


def check_signature(payload, given):
    return bool(given) and hmac.compare_digest(sign(payload), given)


def _base():
    return (getattr(settings, "BASE_URL", "") or "https://mixmint.site").rstrip("/")


def trigger(action, kind, content_id):
    """Start a transfer in a separate request and return at once."""
    payload = {"action": action, "kind": kind, "content_id": content_id}
    try:
        requests.post(f"{_base()}/vault/run/", json=payload, headers={"X-Vault-Sig": sign(payload)}, timeout=1.5)
    except requests.exceptions.ReadTimeout:
        pass  # expected: the other request keeps running
    except Exception as exc:
        logger.error("Vault trigger failed (%s)", type(exc).__name__)
        return False
    return True


# ─────────────────────────────── Telethon plumbing ───────────────────────────────
class _ExactReader:
    """Telethon wants read(n) to return exactly n bytes until the end; network streams may return less."""

    def __init__(self, body):
        self.body = body

    def read(self, n=-1):
        if n is None or n < 0:
            return self.body.read()
        chunks, got = [], 0
        while got < n:
            chunk = self.body.read(n - got)
            if not chunk:
                break
            chunks.append(chunk)
            got += len(chunk)
        return b"".join(chunks)


def _client_class():
    from telethon import TelegramClient

    return TelegramClient


_SESSION = {}


def _load_session():
    """Read the saved login before entering asyncio (the ORM can't be used inside the event loop)."""
    from .models import PlatformSettings

    _SESSION["value"] = PlatformSettings.load().tg_mtproto_session or ""
    _SESSION["new"] = None


def _store_session():
    from .models import PlatformSettings

    new = _SESSION.get("new")
    if new and new != _SESSION.get("value"):
        PlatformSettings.objects.filter(pk=1).update(tg_mtproto_session=new)


async def _connect():
    from telethon.sessions import StringSession

    from . import support

    try:
        session = StringSession(_SESSION.get("value") or "")
    except ValueError:  # damaged saved login: log in again
        session = StringSession("")
    client = _client_class()(
        session, int(settings.TELEGRAM_API_ID), settings.TELEGRAM_API_HASH,
        connection_retries=3, request_retries=3, flood_sleep_threshold=30,
    )
    await client.connect()
    if not await client.is_user_authorized():
        await client.sign_in(bot_token=support._token())
    _SESSION["new"] = client.session.save()
    return client


async def _channel(client, chat_id):
    """Private channel from its Bot API id (-100…). Bots may look up channels they're in by id alone."""
    from telethon.tl import functions, types

    raw = int(str(chat_id).replace("-100", "", 1)) if str(chat_id).startswith("-100") else abs(int(chat_id))
    try:
        return await client.get_input_entity(types.PeerChannel(raw))
    except Exception:
        res = await client(functions.channels.GetChannelsRequest([types.InputChannel(raw, 0)]))
        chat = res.chats[0]
        return types.InputPeerChannel(chat.id, chat.access_hash)


def _run(coro):
    _load_session()
    try:
        return asyncio.run(coro)
    finally:
        _store_session()


def _locked(fn):
    def wrapper(*args, **kwargs):
        if not cache.add(LOCK_KEY, time.time(), timeout=LOCK_SECONDS):
            return {"ok": False, "busy": True, "error": "vault busy"}
        try:
            return fn(*args, **kwargs)
        finally:
            cache.delete(LOCK_KEY)

    return wrapper


# ─────────────────────────────── jobs ───────────────────────────────
@_locked
def archive(kind, item, chat_id, caption, filename):
    """R2 → channel, streamed (no temp files). Returns a result dict like the vault worker's."""
    from apps.core import r2

    async def go():
        from telethon import utils

        client = await _connect()
        try:
            entity = await _channel(client, chat_id)
            obj = r2.client().get_object(Bucket=settings.R2_PRIVATE_BUCKET, Key=item.file_key)
            size = int(obj["ContentLength"])
            uploaded = await client.upload_file(_ExactReader(obj["Body"]), file_size=size, file_name=filename)
            msg = await client.send_file(entity, uploaded, caption=caption[:1000], force_document=True, silent=True)
            doc = getattr(getattr(msg, "media", None), "document", None)
            file_id = utils.pack_bot_file_id(doc) if doc else ""
            return {"ok": True, "message_id": msg.id, "file_id": file_id or "", "file_unique_id": "", "size": size}
        finally:
            await client.disconnect()

    try:
        return _run(go())
    except Exception as exc:
        _forget_bad_session(exc)
        logger.error("MTProto archive failed for %s %s (%s)", kind, item.id, type(exc).__name__)
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:150]}"}


@_locked
def restore(kind, item, chat_id, message_id):
    """Channel post → R2 multipart upload, streamed."""
    from apps.core import r2

    async def go():
        client = await _connect()
        s3 = r2.client()
        bucket, key = settings.R2_PRIVATE_BUCKET, item.file_key
        upload_id = None
        try:
            entity = await _channel(client, chat_id)
            msg = await client.get_messages(entity, ids=int(message_id))
            doc = getattr(getattr(msg, "media", None), "document", None) if msg else None
            if doc is None:
                raise RuntimeError("channel post has no file (deleted?)")
            upload_id = s3.create_multipart_upload(Bucket=bucket, Key=key)["UploadId"]
            parts, buf, n, total = [], bytearray(), 1, 0
            async for chunk in client.iter_download(doc, request_size=512 * 1024):
                buf += chunk
                total += len(chunk)
                while len(buf) >= PART:
                    etag = s3.upload_part(Bucket=bucket, Key=key, UploadId=upload_id, PartNumber=n, Body=bytes(buf[:PART]))["ETag"]
                    parts.append({"ETag": etag, "PartNumber": n})
                    del buf[:PART]
                    n += 1
            if buf or not parts:
                etag = s3.upload_part(Bucket=bucket, Key=key, UploadId=upload_id, PartNumber=n, Body=bytes(buf))["ETag"]
                parts.append({"ETag": etag, "PartNumber": n})
            s3.complete_multipart_upload(Bucket=bucket, Key=key, UploadId=upload_id, MultipartUpload={"Parts": parts})
            upload_id = None
            return {"ok": True, "size": total}
        finally:
            if upload_id:
                try:
                    s3.abort_multipart_upload(Bucket=bucket, Key=key, UploadId=upload_id)
                except Exception:
                    pass
            await client.disconnect()

    try:
        return _run(go())
    except Exception as exc:
        _forget_bad_session(exc)
        logger.error("MTProto restore failed for %s %s (%s: %s)", kind, item.id, type(exc).__name__, str(exc)[:200])
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:150]}"}


def check():
    """Admin 'Test connection': can the bot log in over MTProto? Returns (ok, detail)."""
    if not configured():
        return False, "TELEGRAM_API_ID / TELEGRAM_API_HASH not set"

    async def go():
        client = await _connect()
        try:
            me = await client.get_me()
            return True, f"logged in as @{getattr(me, 'username', '') or me.id}"
        finally:
            await client.disconnect()

    if not cache.add(LOCK_KEY, time.time(), timeout=60):
        return True, "a transfer is running right now"
    try:
        return _run(go())  # noqa: the coroutine is created before _run loads the session; fine
    except Exception as exc:
        _forget_bad_session(exc)
        return False, f"{type(exc).__name__}: {str(exc)[:150]}"
    finally:
        cache.delete(LOCK_KEY)


def _forget_bad_session(exc):
    if any(s in type(exc).__name__ for s in ("AuthKey", "Unauthorized", "SessionRevoked")):
        from .models import PlatformSettings

        PlatformSettings.objects.filter(pk=1).update(tg_mtproto_session="")
