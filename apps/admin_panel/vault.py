"""
Telegram vault: a second, private copy of every file DJs upload.

    DJ browser --PUT--> R2 (private bucket)  <-- buyers always download from here (short-lived signed link)
                          |
                          +--bot--> private channel "singles"  (one post per track: file + caption #T12)
                          +--bot--> private channel "zips"     (one post per album ZIP:  file + caption #A7)

Why R2 stays the source of downloads: the public Bot API lets a bot SEND files up to 50 MB but
only FETCH files up to 20 MB, and Telegram links would expose the bot token. So:
  * files ≤ 50 MB are posted to the channel as a backup (and a searchable catalogue for the admin);
  * bigger files get a text post in the channel (title, DJ, size, R2 key) and live in R2 only;
  * if an R2 object ever goes missing, files ≤ 20 MB are restored from the channel automatically
    the next time someone downloads them, and the buyer still gets a temporary R2 link.
With a self-hosted Bot API server (TELEGRAM_API_BASE) both limits rise to 2 GB.

Linking a channel (once each): add the bot to the private channel as an admin, then post
`/link singles <code>` or `/link zips <code>` there. The code is shown on Admin → Support, so
nobody else can point the vault at their own channel.
"""

import hashlib
import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger("mixmint")
MB = 1024 * 1024
KIND_CHANNEL = {"track": "singles", "album": "zips"}


# ─────────────────────────────── config ───────────────────────────────
def api_base():
    return (getattr(settings, "TELEGRAM_API_BASE", "") or "https://api.telegram.org").rstrip("/")


def self_hosted():
    return "api.telegram.org" not in api_base()


def send_limit():
    return (2000 if self_hosted() else 49) * MB  # 50 MB minus multipart overhead


def fetch_limit():
    return (2000 if self_hosted() else 20) * MB


def link_code():
    return hashlib.sha256(f"tg-vault:{settings.SECRET_KEY}".encode()).hexdigest()[:8]


def channels():
    from .models import PlatformSettings

    ps = PlatformSettings.load()
    return {
        "track": getattr(settings, "TELEGRAM_SINGLES_CHANNEL_ID", "") or ps.tg_singles_channel_id,
        "album": getattr(settings, "TELEGRAM_ZIPS_CHANNEL_ID", "") or ps.tg_zips_channel_id,
    }


def enabled(kind):
    from . import support

    return bool(support._token() and channels().get(kind))


def _url(method):
    from . import support

    return f"{api_base()}/bot{support._token()}/{method}"


def _call(method, *, data=None, files=None, timeout=20):
    """Bot API call that never raises and never logs the URL (it contains the token)."""
    try:
        r = requests.post(_url(method), data=data, files=files, timeout=timeout)
        body = r.json()
    except Exception as exc:
        logger.error("Telegram vault %s failed (%s).", method, type(exc).__name__)
        return None, type(exc).__name__
    if body.get("ok"):
        return body.get("result"), ""
    return None, str(body.get("description") or "error")[:200]


# ─────────────────────────────── items ───────────────────────────────
def _model(kind):
    if kind == "track":
        from apps.tracks.models import Track

        return Track
    from apps.albums.models import AlbumPack

    return AlbumPack


def _r2():
    from apps.core import r2

    return r2.client()


def _caption(kind, item, size):
    tag = f"#{'T' if kind == 'track' else 'A'}{item.id}"
    dj = getattr(item.dj, "dj_name", "")
    price = f"₹{item.price:.0f}" if item.price else "Free"
    return (f"{tag} {item.title}\n{dj} · {price} · {size / MB:.1f} MB\nkey: {item.file_key}")[:1000]


def _filename(kind, item):
    ext = (item.file_key.rsplit(".", 1)[-1] or "bin").lower()[:5]
    safe = "".join(c if c.isalnum() or c in " -_()" else "_" for c in item.title).strip()[:80] or "file"
    dj = "".join(c if c.isalnum() or c in " -_" else "_" for c in getattr(item.dj, "dj_name", "")).strip()[:40]
    return f"{dj} - {safe}.{ext}" if dj else f"{safe}.{ext}"


def archive(kind, item, force=False):
    """Post one uploaded file to its channel. Returns the VaultFile row, or None when the vault is off."""
    from .models import VaultFile

    channel = channels().get(kind)
    if not channel or not item.file_key or not enabled(kind):
        return None
    rec, _ = VaultFile.objects.get_or_create(content_type=kind, content_id=item.id)
    if rec.status in ("archived", "too_large") and rec.file_key == item.file_key and not force:
        return rec
    rec.channel_id, rec.file_key, rec.error = channel, item.file_key, ""
    bucket = settings.R2_PRIVATE_BUCKET
    try:
        size = item.file_size or int(_r2().head_object(Bucket=bucket, Key=item.file_key)["ContentLength"])
    except Exception as exc:
        rec.status, rec.error = "failed", f"R2: {type(exc).__name__}"
        rec.save()
        return rec
    rec.size = size
    caption = _caption(kind, item, size)

    if size > send_limit():
        msg, err = _call("sendMessage", data={
            "chat_id": channel, "disable_notification": "true",
            "text": caption + "\n⚠ Over the bot's 50 MB upload limit: kept in R2 only.",
        })
        rec.status = "too_large" if msg else "failed"
        rec.message_id = (msg or {}).get("message_id")
        rec.error = err
        rec.save()
        return rec

    try:
        body = _r2().get_object(Bucket=bucket, Key=item.file_key)["Body"]
    except Exception as exc:
        rec.status, rec.error = "failed", f"R2: {type(exc).__name__}"
        rec.save()
        return rec
    msg, err = _call(
        "sendDocument",
        data={"chat_id": channel, "caption": caption, "disable_notification": "true",
              "disable_content_type_detection": "true"},
        files={"document": (_filename(kind, item), body)},
        timeout=180,
    )
    doc = (msg or {}).get("document") or (msg or {}).get("audio") or {}
    if msg and doc.get("file_id"):
        rec.status, rec.message_id = "archived", msg.get("message_id")
        rec.file_id, rec.file_unique_id = doc["file_id"], doc.get("file_unique_id", "")
    else:
        rec.status, rec.error = "failed", err or "No file in reply"
    rec.save()
    return rec


def archive_after_upload(kind, item):
    """Called right after a DJ saves an upload. Never breaks the upload."""
    try:
        return archive(kind, item)
    except Exception:
        logger.exception("Vault archive failed for %s %s", kind, item.id)
        return None


def restore(kind, item):
    """Put a missing R2 object back from the channel copy. True when R2 has the file again."""
    from .models import VaultFile

    rec = VaultFile.objects.filter(content_type=kind, content_id=item.id, status="archived").first()
    if not rec or not rec.file_id or rec.file_key != item.file_key or (rec.size or 0) > fetch_limit():
        return False
    info, err = _call("getFile", data={"file_id": rec.file_id})
    path = (info or {}).get("file_path")
    if not path:
        logger.error("Vault restore: getFile failed for %s %s (%s)", kind, item.id, err)
        return False
    from . import support

    try:
        r = requests.get(f"{api_base()}/file/bot{support._token()}/{path}", timeout=120)
        r.raise_for_status()
        _r2().put_object(Bucket=settings.R2_PRIVATE_BUCKET, Key=item.file_key, Body=r.content)
    except Exception as exc:
        logger.error("Vault restore failed for %s %s (%s)", kind, item.id, type(exc).__name__)
        return False
    VaultFile.objects.filter(pk=rec.pk).update(restored_count=rec.restored_count + 1)
    from . import support as s

    s.tg_send(s.admin_chat_id(), f"♻ Restored {'track' if kind == 'track' else 'album'} #{item.id} “{item.title}” to R2 from the vault.")
    return True


def sweep(budget_seconds=240, limit=200):
    """Archive uploads the vault hasn't got yet (backfill + retries). Returns counts."""
    from .models import VaultFile

    started, done = time.monotonic(), {"archived": 0, "too_large": 0, "failed": 0}
    for kind in ("track", "album"):
        if not enabled(kind):
            continue
        have = VaultFile.objects.filter(content_type=kind, status__in=["archived", "too_large"]).values_list("content_id", flat=True)
        todo = (_model(kind).objects.filter(is_deleted=False).exclude(file_key="").exclude(file_key__isnull=True)
                .exclude(id__in=list(have)).select_related("dj").order_by("id")[:limit])
        for item in todo:
            if time.monotonic() - started > budget_seconds:
                return done
            rec = archive(kind, item)
            if rec:
                done[rec.status] = done.get(rec.status, 0) + 1
    return done


def status():
    from .models import PlatformSettings, VaultFile

    ps = PlatformSettings.load()
    counts = {k: VaultFile.objects.filter(status=k).count() for k in ("archived", "too_large", "failed")}
    return {
        "singles": ps.tg_singles_channel_id, "singles_title": ps.tg_singles_channel_title,
        "zips": ps.tg_zips_channel_id, "zips_title": ps.tg_zips_channel_title,
        "code": link_code(), "counts": counts, "self_hosted": self_hosted(),
        "send_mb": send_limit() // MB, "fetch_mb": fetch_limit() // MB,
    }


# ─────────────────────────────── webhook ───────────────────────────────
def handle_channel_update(update):
    """channel_post (/link ...) and my_chat_member (bot added to a channel). True when handled."""
    from . import support

    member = update.get("my_chat_member")
    if member:
        chat = member.get("chat") or {}
        new = (member.get("new_chat_member") or {}).get("status")
        if chat.get("type") == "channel" and new == "administrator":
            support.tg_send(support.admin_chat_id(), (
                f"The bot was added to the channel “{chat.get('title', '')}”.\n"
                f"To store uploads there, post in that channel:\n/link singles {link_code()}\nor\n/link zips {link_code()}"))
        return True

    post = update.get("channel_post")
    if not post:
        return False
    text = (post.get("text") or "").strip()
    chat = post.get("chat") or {}
    parts = text.split()
    if len(parts) != 3 or parts[0].split("@")[0] != "/link" or parts[1] not in ("singles", "zips"):
        return True  # ignore normal channel posts (including the bot's own archive posts)
    if parts[2] != link_code():
        _call("sendMessage", data={"chat_id": chat.get("id"), "text": "That link code is wrong. Copy it from Admin → Support."})
        return True
    from .models import PlatformSettings

    ps = PlatformSettings.load()
    cid, title = str(chat.get("id")), (chat.get("title") or "")[:120]
    if parts[1] == "singles":
        ps.tg_singles_channel_id, ps.tg_singles_channel_title = cid, title
    else:
        ps.tg_zips_channel_id, ps.tg_zips_channel_title = cid, title
    ps.save()
    what = "single tracks" if parts[1] == "singles" else "album ZIPs"
    _call("sendMessage", data={"chat_id": cid, "text": f"✓ MixMint will store every uploaded {what} in this channel."})
    support.tg_send(support.admin_chat_id(), f"✓ Vault linked: “{title}” now stores {what}.")
    return True
