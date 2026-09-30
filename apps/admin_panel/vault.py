"""
Telegram vault: private Telegram channels keep the permanent copy of every upload; Cloudflare R2
is only a holding area that buyers download from.

    DJ browser --PUT--> R2 --(vault worker)--> Telegram channel   singles: tracks · zips: album ZIPs
                        |                                           (permanent, file_id kept here)
                        +-- buyer downloads with a temporary R2 link while the file is held in R2

    How long a file stays in R2 (PlatformSettings, editable on Admin → Support):
      * normal release  : vault_hold_days (10) after upload
      * limited drop    : until it sells out (and at least vault_hold_days)
      * fetched back    : vault_rehold_days (3) after the last buyer asked for it
    After that the R2 copy is deleted, but only when the channel copy is confirmed and can be
    fetched back. When a buyer asks for an evicted file, the vault worker pulls it from Telegram
    into R2 again (usually well under a minute) and the buyer gets the same temporary R2 link.

Limits: the public Bot API can send only 50 MB and fetch only 20 MB. The vault worker runs a
Local Bot API Server (vault_worker/, on any small VPS) which raises sending to 2 GB and removes
the fetch limit, so every track and ZIP can live in Telegram. Without the worker the vault still
works for files up to 20 MB; bigger files simply stay in R2.

Linking a channel (once each): add the bot to the private channel as an admin, then post
`/link singles <code>` or `/link zips <code>` there (code shown on Admin → Support).
"""

import hashlib
import hmac
import logging
import time
from datetime import timedelta

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger("mixmint")
MB = 1024 * 1024
JOB_TIMEOUT = timedelta(minutes=30)


# ─────────────────────────────── config ───────────────────────────────
def api_base():
    return (getattr(settings, "TELEGRAM_API_BASE", "") or "https://api.telegram.org").rstrip("/")


def worker_url():
    return (getattr(settings, "VAULT_WORKER_URL", "") or "").rstrip("/")


def worker_secret():
    return getattr(settings, "VAULT_WORKER_SECRET", "") or ""


def has_worker():
    return bool(worker_url() and worker_secret())


def send_limit():
    return (2000 if has_worker() else 49) * MB


def fetch_limit():
    return 2000 * MB if has_worker() else 20 * MB


def link_code():
    return hashlib.sha256(f"tg-vault:{settings.SECRET_KEY}".encode()).hexdigest()[:8]


def _ps():
    from .models import PlatformSettings

    return PlatformSettings.load()


def channels():
    ps = _ps()
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


def _worker(path, payload=None, method="post", timeout=15):
    """Talk to the vault worker. Returns (json, error)."""
    try:
        r = getattr(requests, method)(
            f"{worker_url()}{path}", json=payload, timeout=timeout,
            headers={"Authorization": f"Bearer {worker_secret()}"},
        )
        if r.status_code >= 400:
            return None, f"worker {r.status_code}"
        return r.json(), ""
    except Exception as exc:
        return None, f"worker {type(exc).__name__}"


def verify_worker(request):
    auth = request.headers.get("Authorization", "")
    given = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    return bool(worker_secret()) and hmac.compare_digest(given, worker_secret())


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


def _bucket():
    return settings.R2_PRIVATE_BUCKET


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


def _callback_url():
    base = (getattr(settings, "BASE_URL", "") or "https://mixmint.site").rstrip("/")
    return f"{base}/vault/callback/"


def _first_hold(item):
    uploaded = getattr(item, "created_at", None) or timezone.now()
    return uploaded + timedelta(days=_ps().vault_hold_days)


def _size(item):
    return item.file_size or int(_r2().head_object(Bucket=_bucket(), Key=item.file_key)["ContentLength"])


# ─────────────────────────────── archive (R2 → channel) ───────────────────────────────
def archive(kind, item, force=False):
    """Copy one upload into its channel. Returns the VaultFile row, or None when the vault is off."""
    from .models import VaultFile

    channel = channels().get(kind)
    if not channel or not item.file_key or not enabled(kind):
        return None
    rec, created = VaultFile.objects.get_or_create(
        content_type=kind, content_id=item.id, defaults={"r2_hold_until": _first_hold(item)}
    )
    if rec.file_key == item.file_key and not force:
        if rec.status in ("archived", "too_large"):
            return rec
        if rec.status == "pending" and rec.job_started_at and timezone.now() - rec.job_started_at < JOB_TIMEOUT:
            return rec
    if rec.file_key and rec.file_key != item.file_key:  # DJ replaced the file: new copy, new hold
        rec.r2_present, rec.r2_hold_until, rec.file_id = True, _first_hold(item), ""
    rec.channel_id, rec.file_key, rec.error = channel, item.file_key, ""
    try:
        size = _size(item)
    except Exception as exc:
        rec.status, rec.error = "failed", f"R2: {type(exc).__name__}"
        rec.save()
        return rec
    rec.size = size
    caption = _caption(kind, item, size)

    if size > send_limit():
        msg, err = _call("sendMessage", data={
            "chat_id": channel, "disable_notification": "true",
            "text": caption + "\n⚠ Too big for the bot without the vault worker: kept in R2 only.",
        })
        rec.status = "too_large" if msg else "failed"
        rec.message_id = (msg or {}).get("message_id")
        rec.error = err
        rec.save()
        return rec

    if has_worker():
        job, err = _worker("/jobs", {
            "action": "archive", "kind": kind, "content_id": item.id, "key": item.file_key,
            "bucket": _bucket(), "chat_id": channel, "caption": caption, "filename": _filename(kind, item),
            "callback": _callback_url(),
        })
        rec.status = "pending" if job else "failed"
        rec.job_id, rec.job_started_at, rec.error = (job or {}).get("job_id", ""), timezone.now(), err
        rec.save()
        return rec

    try:
        body = _r2().get_object(Bucket=_bucket(), Key=item.file_key)["Body"]
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
    _apply_archive(rec, msg, err)
    return rec


def _apply_archive(rec, msg, err):
    doc = (msg or {}).get("document") or (msg or {}).get("audio") or {}
    if msg and doc.get("file_id"):
        rec.status, rec.message_id = "archived", msg.get("message_id")
        rec.file_id, rec.file_unique_id = doc["file_id"], doc.get("file_unique_id", "")
        rec.error = ""
    else:
        rec.status, rec.error = "failed", (err or "No file in reply")[:255]
    rec.job_id = ""
    rec.save()


def archive_after_upload(kind, item):
    """Called right after a DJ saves an upload. Never breaks the upload."""
    try:
        return archive(kind, item)
    except Exception:
        logger.exception("Vault archive failed for %s %s", kind, item.id)
        return None


# ─────────────────────────────── restore (channel → R2) ───────────────────────────────
def restorable(rec):
    return bool(rec and rec.status == "archived" and rec.file_id and (rec.size or 0) <= fetch_limit())


def _rehold(rec):
    days = _ps().vault_rehold_days
    until = timezone.now() + timedelta(days=days)
    if not rec.r2_hold_until or rec.r2_hold_until < until:
        rec.r2_hold_until = until


def restore(kind, item):
    """Put the file back into R2 from the channel copy.
    Returns "ready" (in R2 now), "working" (the worker is fetching it) or "" (can't)."""
    from .models import VaultFile

    rec = VaultFile.objects.filter(content_type=kind, content_id=item.id).first()
    if not restorable(rec) or rec.file_key != item.file_key:
        return ""
    if has_worker():
        lock = f"vault_restore_{kind}_{item.id}"
        if cache.get(lock):
            return "working"
        job, err = _worker("/jobs", {
            "action": "restore", "kind": kind, "content_id": item.id, "key": item.file_key,
            "bucket": _bucket(), "file_id": rec.file_id, "callback": _callback_url(),
        })
        if not job:
            logger.error("Vault restore could not start for %s %s (%s)", kind, item.id, err)
            return ""
        cache.set(lock, job.get("job_id", "1"), timeout=15 * 60)
        return "working"

    info, err = _call("getFile", data={"file_id": rec.file_id})
    path = (info or {}).get("file_path")
    if not path:
        logger.error("Vault restore: getFile failed for %s %s (%s)", kind, item.id, err)
        return ""
    from . import support

    try:
        r = requests.get(f"{api_base()}/file/bot{support._token()}/{path}", timeout=120)
        r.raise_for_status()
        _r2().put_object(Bucket=_bucket(), Key=item.file_key, Body=r.content)
    except Exception as exc:
        logger.error("Vault restore failed for %s %s (%s)", kind, item.id, type(exc).__name__)
        return ""
    _mark_restored(rec)
    return "ready"


def _mark_restored(rec):
    rec.r2_present, rec.evicted_at = True, None
    rec.restored_count += 1
    _rehold(rec)
    rec.save()
    cache.delete(f"vault_restore_{rec.content_type}_{rec.content_id}")


def ensure_in_r2(kind, item):
    """Before issuing a buyer's download link. True when R2 has the file (or the vault doesn't
    manage it, so the normal flow decides); False while the worker is fetching it back."""
    from .models import VaultFile

    rec = VaultFile.objects.filter(content_type=kind, content_id=item.id).first()
    if rec is None:
        return True
    if rec.r2_present:
        until = timezone.now() + timedelta(days=_ps().vault_rehold_days)
        if not rec.r2_hold_until or rec.r2_hold_until < until:
            VaultFile.objects.filter(pk=rec.pk).update(r2_hold_until=until)
        return True
    try:  # maybe it came back already (callback raced us)
        _r2().head_object(Bucket=_bucket(), Key=item.file_key)
        _mark_restored(rec)
        return True
    except Exception:
        pass
    return restore(kind, item) == "ready"


# ─────────────────────────────── worker callback ───────────────────────────────
def apply_worker_result(data):
    """The worker reports a finished job (POST /vault/callback/)."""
    from .models import VaultFile

    rec = VaultFile.objects.filter(content_type=data.get("kind"), content_id=data.get("content_id")).first()
    if rec is None:
        return False
    if data.get("action") == "archive":
        if data.get("key") != rec.file_key:
            return False  # stale job for a replaced file
        msg = {"message_id": data.get("message_id"),
               "document": {"file_id": data.get("file_id"), "file_unique_id": data.get("file_unique_id", "")}} if data.get("ok") else None
        _apply_archive(rec, msg, data.get("error", ""))
        return True
    if data.get("action") == "restore":
        if data.get("ok"):
            _mark_restored(rec)
        else:
            cache.delete(f"vault_restore_{rec.content_type}_{rec.content_id}")
            from . import support

            support.tg_send(support.admin_chat_id(), f"⚠ Vault couldn't fetch {rec.content_type} #{rec.content_id} back into R2: {data.get('error', '')[:200]}")
        return True
    return False


# ─────────────────────────────── eviction (R2 holding area) ───────────────────────────────
def _limited_drop_live(kind, item):
    if not getattr(item, "copies_limit", None) or not item.is_active or item.is_deleted:
        return False
    from apps.core.catalog import sold_out

    return not sold_out(item, kind)


def evict(now=None, limit=500):
    """Delete R2 copies whose hold has ended and whose Telegram copy is confirmed. Returns count."""
    from .models import VaultFile

    ps = _ps()
    if not ps.vault_evict_enabled:
        return 0
    now = now or timezone.now()
    evicted = 0
    due = VaultFile.objects.filter(status="archived", r2_present=True, r2_hold_until__lt=now).exclude(file_id="")[:limit]
    for rec in due:
        if not restorable(rec):
            continue
        item = _model(rec.content_type).objects.filter(pk=rec.content_id).first()
        if item is None or item.file_key != rec.file_key:
            continue
        if _limited_drop_live(rec.content_type, item):
            continue  # limited launch: stays in R2 until it sells out
        uploaded = getattr(item, "created_at", None)
        if uploaded and uploaded + timedelta(days=ps.vault_hold_days) > now:
            continue  # hold was made longer in settings after this file was uploaded
        try:
            _r2().delete_object(Bucket=_bucket(), Key=rec.file_key)
        except Exception as exc:
            logger.error("Vault evict failed for %s %s (%s)", rec.content_type, rec.content_id, type(exc).__name__)
            continue
        rec.r2_present, rec.evicted_at = False, now
        rec.save(update_fields=["r2_present", "evicted_at", "updated_at"])
        evicted += 1
    return evicted


# ─────────────────────────────── sweep + status ───────────────────────────────
def sweep(budget_seconds=240, limit=200):
    """Archive uploads the vault hasn't got yet (backfill + retries), then free R2. Returns counts."""
    from .models import VaultFile

    started, done = time.monotonic(), {"archived": 0, "pending": 0, "too_large": 0, "failed": 0}
    for kind in ("track", "album"):
        if not enabled(kind):
            continue
        have = VaultFile.objects.filter(content_type=kind, status__in=["archived", "pending"]).values_list("content_id", flat=True)
        if not has_worker():  # without the worker, "too big" is final; with it, retry those
            have = VaultFile.objects.filter(content_type=kind, status__in=["archived", "pending", "too_large"]).values_list("content_id", flat=True)
        todo = (_model(kind).objects.filter(is_deleted=False).exclude(file_key="").exclude(file_key__isnull=True)
                .exclude(id__in=list(have)).select_related("dj").order_by("id")[:limit])
        for item in todo:
            if time.monotonic() - started > budget_seconds:
                return done
            rec = archive(kind, item, force=True)
            if rec:
                done[rec.status] = done.get(rec.status, 0) + 1
    done["freed"] = evict()
    return done


def worker_health():
    """Admin-only view of the vault server (vault.mixmint.site itself shows nothing to visitors)."""
    if not has_worker():
        return None
    data, err = _worker("/health", method="get", timeout=5)
    return data or {"bot": False, "r2": False, "error": err}


def status():
    from .models import VaultFile

    ps = _ps()
    counts = {k: VaultFile.objects.filter(status=k).count() for k in ("archived", "pending", "too_large", "failed")}
    counts["in_r2"] = VaultFile.objects.filter(status="archived", r2_present=True).count()
    counts["telegram_only"] = VaultFile.objects.filter(status="archived", r2_present=False).count()
    return {
        "singles": ps.tg_singles_channel_id, "singles_title": ps.tg_singles_channel_title,
        "zips": ps.tg_zips_channel_id, "zips_title": ps.tg_zips_channel_title,
        "code": link_code(), "counts": counts, "worker": has_worker(),
        "send_mb": send_limit() // MB, "fetch_mb": fetch_limit() // MB,
        "evict": ps.vault_evict_enabled, "hold_days": ps.vault_hold_days, "rehold_days": ps.vault_rehold_days,
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
        return True  # ignore normal channel posts
    if parts[2] != link_code():
        _call("sendMessage", data={"chat_id": chat.get("id"), "text": "That link code is wrong. Copy it from Admin → Support."})
        return True
    ps = _ps()
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
