"""DJ promo videos: Telegram → MixMint template → Instagram Reel (with collab invites) + YouTube Short.

Only for releases, and only when the DJ asks for it while uploading (Upload page → "Free promo").

    1. Upload page: DJ ticks "Free promo", picks a template and who to collab with
       (Instagram: up to 3 accounts, the API limit; YouTube: up to 10 channels).
    2. Promo page: "Send in Telegram" (t.me/<bot>?start=pv_…) or upload the clip right there.
       The bot takes clips up to 20 MB (Telegram's bot download limit); bigger ones go through the page.
    3. The clip lands in R2 (private) and GitHub Actions renders it (.github/workflows/promo-render.yml:
       ffmpeg + the template in tools/promo/render.py). The job gets a signed, expiring link to this
       site, so GitHub needs no secrets of ours.
    4. The admin gets the finished video in Telegram with "Post" / "Don't post" (or it posts by itself
       when Admin → Settings → Promo videos → auto-post is on). A daily cap keeps us inside Instagram
       and YouTube API limits; extra approved videos wait for the next day.
    5. Posting runs in its own request (up to 300 s on Vercel): Instagram Reel with `collaborators`
       (each DJ account gets a collab invite), YouTube Short with every channel credited, plus the
       public Telegram channel. YouTube has no API for collab invites, so the admin gets a reminder
       with the channels to invite in YouTube Studio.
"""

import hashlib
import hmac
import json
import logging
import re
import time

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("mixmint")

IG_MAX = 3
YT_MAX = 10
TG_BOT_MAX = 20 * 1024 * 1024  # Bot API getFile limit
LINK_TTL = 7 * 24 * 3600
JOB_TTL = 6 * 3600
VIDEO_EXT = {"mp4": "video/mp4", "mov": "video/quicktime", "m4v": "video/x-m4v", "webm": "video/webm"}
DEFAULTS = {"enabled": True, "auto_approve": False, "daily_cap": 5}
GRAPH = "https://graph.facebook.com/v23.0"


# ─────────────────────────────── config ───────────────────────────────
def cfg():
    from .models import SystemSetting

    row = SystemSetting.objects.filter(key="promo").first()
    out = dict(DEFAULTS)
    if row and isinstance(row.value, dict):
        out.update(row.value)
    return out


def save_cfg(**kw):
    from .models import SystemSetting

    val = cfg()
    val.update(kw)
    SystemSetting.objects.update_or_create(key="promo", defaults={"value": val})
    return val


def renderer_ready():
    return bool(getattr(settings, "PROMO_GITHUB_REPO", "") and getattr(settings, "PROMO_GITHUB_TOKEN", ""))


def ig_ready():
    return bool(getattr(settings, "INSTAGRAM_USER_ID", "") and getattr(settings, "INSTAGRAM_ACCESS_TOKEN", ""))


def yt_ready():
    return bool(getattr(settings, "YOUTUBE_CLIENT_ID", "") and getattr(settings, "YOUTUBE_CLIENT_SECRET", "")
                and getattr(settings, "YOUTUBE_REFRESH_TOKEN", ""))


def fb_ready():
    return bool(getattr(settings, "FACEBOOK_PAGE_ID", "") and getattr(settings, "FACEBOOK_PAGE_ACCESS_TOKEN", ""))


def readiness():
    return {"renderer": renderer_ready(), "instagram": ig_ready(), "youtube": yt_ready(), "facebook": fb_ready(),
            "telegram": bool(getattr(settings, "TELEGRAM_BOT_TOKEN", "") or getattr(settings, "TELEGRAM_BOT_USERNAME", ""))}


def site():
    return (getattr(settings, "BASE_URL", "") or "https://mixmint.site").rstrip("/")


# ─────────────────────────────── collab handles ───────────────────────────────
IG_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")
YT_RE = re.compile(r"^[A-Za-z0-9._-]{3,30}$")
OWN = {"mixmint", "mixmint.site", "mixmintsite", "mixmint_site"}


def _handle(raw):
    raw = (raw or "").strip()
    m = re.search(r"(?:instagram\.com|youtube\.com)/@?([A-Za-z0-9._-]+)", raw)
    if m:
        raw = m.group(1)
    return raw.lstrip("@").strip().strip("/")


def clean_handles(raw, platform):
    """'@a, b  https://instagram.com/c' -> ['a', 'b', 'c'] (valid, unique, not MixMint, capped at the platform limit)."""
    rx, limit = (IG_RE, IG_MAX) if platform == "ig" else (YT_RE, YT_MAX)
    items = raw if isinstance(raw, (list, tuple)) else re.split(r"[\s,;\n]+", raw or "")
    out = []
    for item in items:
        h = _handle(item)
        if h and rx.match(h) and h.lower() not in OWN and h.lower() not in {x.lower() for x in out}:
            out.append(h)
    return out[:limit]


def handle_errors(raw, platform):
    """Human message when the DJ typed more than allowed or something invalid, else ''."""
    rx, limit, name = (IG_RE, IG_MAX, "Instagram") if platform == "ig" else (YT_RE, YT_MAX, "YouTube")
    items = [i for i in re.split(r"[\s,;\n]+", raw or "") if i.strip()]
    bad = [i for i in items if not rx.match(_handle(i))]
    if bad:
        return f"{name}: “{bad[0][:40]}” isn't a valid {'username' if platform == 'ig' else 'channel handle'}."
    if len({_handle(i).lower() for i in items}) > limit:
        return f"{name} allows up to {limit} collaborators on one post."
    return ""


# ─────────────────────────────── create / lookup ───────────────────────────────
def create(item, kind, *, ig, yt, template="mint", rights=True):
    from .models import PromoVideo

    template = template if template in dict(PromoVideo.TEMPLATES) else "mint"
    pv, _ = PromoVideo.objects.update_or_create(
        content_type=kind, content_id=item.pk,
        defaults={"dj": item.dj, "title": item.title[:255], "template": template, "rights_confirmed": bool(rights),
                  "ig_collabs": clean_handles(ig, "ig"), "yt_collabs": clean_handles(yt, "yt"), "status": "waiting"},
    )
    return pv


def item_for(pv):
    if pv.content_type == "album":
        from apps.albums.models import AlbumPack

        return AlbumPack.objects.filter(pk=pv.content_id).select_related("dj").first()
    from apps.tracks.models import Track

    return Track.objects.filter(pk=pv.content_id).select_related("dj").first()


def item_url(pv):
    return f"{site()}/{'albums' if pv.content_type == 'album' else 'tracks'}/{pv.content_id}/"


def page_url(pv):
    return f"{site()}/dashboard/promo/{pv.pk}/"


def price_text(item):
    if item is None or not item.price:
        return "Free"
    return f"₹{int(item.price) if item.price == int(item.price) else item.price}"


# ─────────────────────────────── signed links ───────────────────────────────
def _b36(n):
    chars, out = "0123456789abcdefghijklmnopqrstuvwxyz", ""
    n = int(n)
    while True:
        n, r = divmod(n, 36)
        out = chars[r] + out
        if not n:
            return out


def _sig(*parts, n=12):
    msg = ":".join(str(p) for p in parts)
    return hmac.new(f"promo:{settings.SECRET_KEY}".encode(), msg.encode(), hashlib.sha256).hexdigest()[:n]


def start_payload(pv):
    ts = _b36(int(time.time()))
    return f"pv_{_b36(pv.pk)}_{ts}_{_sig('tg', pv.pk, ts)}"


def from_payload(payload):
    from .models import PromoVideo

    try:
        _, pid36, ts36, sig = payload.strip().split("_", 3)
        pid, ts = int(pid36, 36), int(ts36, 36)
    except ValueError:
        return None
    if not hmac.compare_digest(_sig("tg", pid, ts36), sig) or time.time() - ts > LINK_TTL:
        return None
    return PromoVideo.objects.filter(pk=pid).select_related("dj__profile").first()


def tg_link(pv):
    from .telegram import bot_deep_link

    return bot_deep_link(start_payload(pv))


def job_token(pv):
    exp = int(time.time()) + JOB_TTL
    return f"{exp}.{_sig('job', pv.pk, exp, n=32)}"


def check_job_token(pv, token):
    try:
        exp, sig = str(token).split(".", 1)
        exp = int(exp)
    except ValueError:
        return False
    return exp > time.time() and hmac.compare_digest(_sig("job", pv.pk, exp, n=32), sig)


def run_sig(pid):
    return _sig("run", pid, n=32)


# ─────────────────────────────── receiving the clip ───────────────────────────────
def _r2():
    from apps.core import r2

    return r2


def raw_key(pv, ext):
    return f"promo/{pv.dj_id}/{pv.pk}-{int(time.time())}-raw.{ext}"


def presign_raw(pv, filename, size):
    r2 = _r2()
    ext = (filename or "").rsplit(".", 1)[-1].lower()
    if ext not in VIDEO_EXT:
        raise r2.UploadError("Please choose an MP4, MOV, M4V or WEBM video.")
    try:
        size = int(size)
    except (TypeError, ValueError):
        raise r2.UploadError("Could not read the file size.")
    limit = int(getattr(settings, "MAX_PROMO_SIZE_MB", 300)) * 1024 * 1024
    if size <= 0 or size > limit:
        raise r2.UploadError(f"The video must be under {limit // (1024 * 1024)} MB.")
    if not r2.configured():
        raise r2.UploadError("File storage isn't set up yet.")
    key = raw_key(pv, ext)
    url = r2.client().generate_presigned_url(
        "put_object", Params={"Bucket": settings.R2_PRIVATE_BUCKET, "Key": key, "ContentType": VIDEO_EXT[ext]}, ExpiresIn=3600)
    return {"key": key, "url": url, "headers": {"Content-Type": VIDEO_EXT[ext]}}


def web_uploaded(pv, key):
    r2 = _r2()
    if not key.startswith(f"promo/{pv.dj_id}/{pv.pk}-") or ".." in key:
        raise r2.UploadError("Upload not found. Please choose the video again.")
    try:
        r2.client().head_object(Bucket=settings.R2_PRIVATE_BUCKET, Key=key)
    except Exception:
        raise r2.UploadError("The upload didn't finish. Please try again.")
    _received(pv, key, "web")


def _received(pv, key, source):
    pv.raw_key, pv.source, pv.status, pv.error = key, source, "received", ""
    pv.output_key = pv.thumb_key = ""
    pv.save()
    start_render(pv)


def attach_chat(pv, chat_id):
    pv.tg_chat_id = str(chat_id)
    pv.save(update_fields=["tg_chat_id", "updated_at"])


def _send(chat_id, text, buttons=None):
    from . import bot

    bot.send(chat_id, text, buttons)


def waiting_for_chat(chat_id):
    from .models import PromoVideo

    return PromoVideo.objects.filter(tg_chat_id=str(chat_id), status__in=("waiting", "failed")).order_by("-updated_at").first()


def on_telegram_video(chat_id, msg):
    """A video (or video file) arrived in a private chat. Returns True when it was a promo clip."""
    media = msg.get("video") or msg.get("animation")
    doc = msg.get("document") or {}
    if not media and str(doc.get("mime_type", "")).startswith("video/"):
        media = doc
    if not media:
        return False
    pv = waiting_for_chat(chat_id)
    if pv is None:
        _send(chat_id, "To get a promo video posted, tick “Free promo” when you upload a release on mixmint.site, "
                       "then tap “Send in Telegram” on the next page.")
        return True
    size = int(media.get("file_size") or 0)
    if size > TG_BOT_MAX:
        _send(chat_id, f"That video is {size // (1024 * 1024)} MB. Telegram lets bots fetch up to 20 MB, so please upload it "
                       "on the promo page instead (or send a shorter clip).", [[("Upload on mixmint.site", page_url(pv))]])
        return True
    from . import support

    try:
        info = support.tg("getFile", {"file_id": media["file_id"]}) or {}
        path = (info.get("result") or info).get("file_path")
        if not path:
            raise ValueError("no file_path")
        from .vault import api_base

        r = requests.get(f"{api_base()}/file/bot{support._token()}/{path}", timeout=90)
        r.raise_for_status()
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else "mp4"
        ext = ext if ext in VIDEO_EXT else "mp4"
        key = raw_key(pv, ext)
        _r2().client().put_object(Bucket=settings.R2_PRIVATE_BUCKET, Key=key, Body=r.content, ContentType=VIDEO_EXT[ext])
    except Exception as exc:
        logger.error("Promo: Telegram video download failed for %s (%s)", pv.pk, type(exc).__name__)
        _send(chat_id, "I couldn't fetch that video. Please send it again, or upload it on the promo page.",
              [[("Promo page", page_url(pv))]])
        return True
    _received(pv, key, "telegram")
    _send(chat_id, f"Got it ✓ Putting “{pv.title}” into the MixMint template now. You'll get the finished video here "
                   "in a few minutes.")
    return True


# ─────────────────────────────── rendering (GitHub Actions) ───────────────────────────────
def start_render(pv):
    if not renderer_ready():
        _admin(f"Promo video for “{pv.title}” ({pv.dj.dj_name}) is waiting: the video renderer isn't connected "
               "(add PROMO_GITHUB_REPO and PROMO_GITHUB_TOKEN in Vercel).")
        return False
    tok = job_token(pv)
    payload = {"event_type": "promo_render", "client_payload": {
        "id": pv.pk, "job_url": f"{site()}/promo/job/{pv.pk}/?t={tok}", "done_url": f"{site()}/promo/job/{pv.pk}/done/?t={tok}"}}
    try:
        r = requests.post(f"https://api.github.com/repos/{settings.PROMO_GITHUB_REPO}/dispatches", json=payload, timeout=15,
                          headers={"Authorization": f"Bearer {settings.PROMO_GITHUB_TOKEN}",
                                   "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
        ok = r.status_code == 204
    except Exception as exc:
        ok, r = False, None
        logger.error("Promo render dispatch failed (%s)", type(exc).__name__)
    if not ok:
        pv.status, pv.error = "failed", f"Renderer didn't start (GitHub {getattr(r, 'status_code', 'error')})."
        pv.save()
        _admin(f"Promo render for “{pv.title}” didn't start: {pv.error} Check PROMO_GITHUB_TOKEN.")
        return False
    pv.status = "rendering"
    pv.save(update_fields=["status", "updated_at"])
    return True


def job_info(pv):
    """What the renderer needs: signed links to read the clip and write the result, plus the text."""
    r2 = _r2()
    item = item_for(pv)
    c = r2.client()
    stamp = int(time.time())
    out_key = f"promo/{pv.dj_id}/{pv.pk}-{stamp}.mp4"
    thumb_key = f"promo/{pv.dj_id}/{pv.pk}-{stamp}.jpg"
    cover = str(getattr(item, "cover_url", "") or getattr(item, "cover_image", "") or "")
    return {
        "id": pv.pk,
        "template": pv.template,
        "title": pv.title,
        "dj": pv.dj.dj_name,
        "price": price_text(item),
        "kind": "Sample pack" if getattr(item, "pack_type", "") == "samples" else ("Album" if pv.content_type == "album" else "New drop"),
        "site": site().replace("https://", "").replace("http://", "").replace("www.", ""),
        "cover_url": cover if cover.startswith("https://") else "",
        "max_seconds": 59,
        "raw_url": c.generate_presigned_url("get_object", Params={"Bucket": settings.R2_PRIVATE_BUCKET, "Key": pv.raw_key}, ExpiresIn=JOB_TTL),
        "output": {"key": out_key, "url": c.generate_presigned_url(
            "put_object", Params={"Bucket": settings.R2_PUBLIC_BUCKET, "Key": out_key, "ContentType": "video/mp4"}, ExpiresIn=JOB_TTL)},
        "thumb": {"key": thumb_key, "url": c.generate_presigned_url(
            "put_object", Params={"Bucket": settings.R2_PUBLIC_BUCKET, "Key": thumb_key, "ContentType": "image/jpeg"}, ExpiresIn=JOB_TTL)},
    }


def job_done(pv, data):
    if not data.get("ok"):
        pv.status, pv.error = "failed", str(data.get("error") or "render failed")[:500]
        pv.save()
        _admin(f"Promo render failed for “{pv.title}”: {pv.error}")
        if pv.tg_chat_id:
            _send(pv.tg_chat_id, "Something went wrong while editing your video. Please send it again (MP4, under 60 seconds works best).")
        return
    out, thumb = str(data.get("output_key") or ""), str(data.get("thumb_key") or "")
    prefix = f"promo/{pv.dj_id}/{pv.pk}-"
    if not out.startswith(prefix) or ".." in out:
        pv.status, pv.error = "failed", "Renderer returned an unexpected file."
        pv.save()
        return
    pv.output_key, pv.thumb_key = out, thumb if thumb.startswith(prefix) else ""
    try:
        pv.duration = float(data.get("duration") or 0) or None
    except (TypeError, ValueError):
        pv.duration = None
    pv.status, pv.error = "review", ""
    pv.save()
    _delete(settings.R2_PRIVATE_BUCKET, pv.raw_key)  # the DJ's original isn't kept in the cloud
    rendered(pv)


def video_url(pv):
    """Public link while the video is still in R2 (rendering → posting); afterwards it lives in Telegram."""
    return _r2().public_url(pv.output_key) if pv.output_key else ""


def thumb_url(pv):
    return _r2().public_url(pv.thumb_key) if pv.thumb_key else ""


def rendered(pv):
    """Finished video: show the DJ, then post automatically or ask the admin."""
    from . import bot

    url = video_url(pv)
    who = "You'll get the links here when it's live." if cfg().get("auto_approve") else "The MixMint team gives it a quick look, then it goes live; you'll get the links here."
    _dj(pv, f"Your promo video for “{pv.title}” is ready. {who}", [[("Watch it", url)]] if url else None)
    if cfg().get("auto_approve"):
        approve(pv, "auto")
        return
    from .support import admin_chat_id

    chat = admin_chat_id()
    if not chat:
        return
    collabs = ", ".join("@" + h for h in pv.ig_collabs) or "none"
    caption = (f"🎬 Promo ready: “{pv.title}” by {pv.dj.dj_name}\nInstagram collabs: {collabs}\n"
               f"YouTube credits: {', '.join('@' + h for h in pv.yt_collabs) or 'none'}")
    buttons = {"inline_keyboard": [[{"text": "✅ Post it", "callback_data": f"pvok:{pv.pk}"},
                                    {"text": "✖ Don't post", "callback_data": f"pvno:{pv.pk}"}],
                                   [{"text": "Open release", "url": item_url(pv)}]]}
    ok = bot.send_raw({"chat_id": chat, "video": url, "caption": caption, "reply_markup": buttons, "supports_streaming": True},
                      method="sendVideo") if url else False
    if not ok:
        bot.send_raw({"chat_id": chat, "text": caption + (f"\n{url}" if url else ""), "reply_markup": buttons})


# ─────────────────────────────── approving / queue ───────────────────────────────
def posted_today():
    from .models import PromoVideo

    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return PromoVideo.objects.filter(status__in=("posted", "posting"), updated_at__gte=start).count()


def approve(pv, by):
    if pv.status not in ("review", "queued", "failed") or not pv.output_key:
        return pv.status
    pv.approved_by = by[:120]
    if posted_today() >= int(cfg().get("daily_cap") or DEFAULTS["daily_cap"]):
        pv.status = "queued"
        pv.save()
        return "queued"
    pv.status, pv.error = "posting", ""
    pv.save()
    trigger_publish(pv)
    return "posting"


def reject(pv, by):
    pv.status, pv.approved_by = "rejected", by[:120]
    pv.save()
    if archive(pv):
        cleanup_cloud(pv)
    _plain_channel_post(pv)
    _dj(pv, f"Your promo video for “{pv.title}” wasn't posted on MixMint's channels this time. "
                              "You can still share it yourself. Reply here if you have questions.")


def release_queue():
    """Daily: post approved videos that were over yesterday's cap."""
    from .models import PromoVideo

    n = 0
    for pv in PromoVideo.objects.filter(status="queued").order_by("updated_at"):
        if approve(pv, pv.approved_by or "queue") != "posting":
            break
        n += 1
    return n


def trigger_publish(pv):
    """Run publish() in a separate request (Vercel functions get 300 s) and return at once."""
    try:
        requests.post(f"{site()}/promo/run/", json={"id": pv.pk}, headers={"X-Promo-Sig": run_sig(pv.pk)}, timeout=1.5)
    except requests.exceptions.ReadTimeout:
        pass
    except Exception as exc:
        logger.error("Promo publish trigger failed (%s)", type(exc).__name__)


# ─────────────────────────────── publishing ───────────────────────────────
TAGS_IG = "#DJ #DJRemix #DJEdit #IndianDJ #Remix #NewMusic #MixMint"


def ig_caption(pv, item):
    collabs = " ".join("@" + h for h in pv.ig_collabs)
    return (f"🔥 {pv.title} by {pv.dj.dj_name}\n\n"
            f"🎧 Preview and download on MixMint ({price_text(item)}). Link in bio: mixmint.site\n"
            + (f"\nWith {collabs}\n" if collabs else "") + f"\n{TAGS_IG}")[:2200]


def yt_title(pv):
    base = f"{pv.title} - {pv.dj.dj_name}"
    return (base[:88] + " #shorts") if len(base) > 88 else f"{base} | DJ Remix #shorts"


def yt_description(pv, item):
    credits = "\n".join(f"🎧 @{h}" for h in pv.yt_collabs)
    return (f"{pv.title} by {pv.dj.dj_name}\n\n▶ Preview and download ({price_text(item)}): {item_url(pv)}\n"
            + (f"\nCollab:\n{credits}\n" if credits else "")
            + "\nMixMint: home of DJ releases from India's DJs. Sell your edits: " + site() + "/sell\n\n"
            "#shorts #djremix #djsong #remix #mixmint")[:4900]


def publish(pv):
    """Post to Instagram, YouTube and the Telegram channel. Never raises."""
    item = item_for(pv)
    url = video_url(pv)
    results, errors = {}, []
    if ig_ready():
        try:
            results["ig"] = _post_instagram(pv, item, url)
        except Exception as exc:
            errors.append(f"Instagram: {str(exc)[:200]}")
    if yt_ready():
        try:
            results["yt"] = _post_youtube(pv, item)
        except Exception as exc:
            errors.append(f"YouTube: {str(exc)[:200]}")
    if fb_ready():
        try:
            results["fb"] = _post_facebook(pv, item, url)
        except Exception as exc:
            errors.append(f"Facebook: {str(exc)[:200]}")
    pv.refresh_from_db()
    if results.get("ig"):
        pv.ig_media_id, pv.ig_url = results["ig"]
    if results.get("yt"):
        pv.yt_video_id = results["yt"]
    pv.error = "; ".join(errors)[:500]
    pv.status = "posted" if results else "failed"
    if results:
        pv.posted_at = timezone.now()
    if not ig_ready() and not yt_ready() and not fb_ready():
        pv.error = "Instagram, YouTube and Facebook aren't connected yet (see Admin → Settings → Promo videos)."
    pv.save()
    archive(pv)
    _post_channel(pv, item)
    if pv.asset_file_id:  # safe copy in Telegram: the cloud copy goes
        cleanup_cloud(pv)
    _after_publish(pv)
    return pv.status


def _graph(method, path, **data):
    data["access_token"] = settings.INSTAGRAM_ACCESS_TOKEN
    base = (getattr(settings, "INSTAGRAM_GRAPH_BASE", "") or GRAPH).rstrip("/")
    r = getattr(requests, method)(f"{base}/{path}", **({"params": data} if method == "get" else {"data": data}), timeout=30)
    body = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in body:
        raise RuntimeError((body.get("error") or {}).get("message") or f"HTTP {r.status_code}")
    return body


def _post_instagram(pv, item, url, wait=170):
    uid = settings.INSTAGRAM_USER_ID
    fields = {"media_type": "REELS", "video_url": url, "caption": ig_caption(pv, item), "share_to_feed": "true"}
    if pv.thumb_key:
        fields["cover_url"] = thumb_url(pv)
    collab_note = ""
    if pv.ig_collabs:
        try:
            container = _graph("post", f"{uid}/media", collaborators=json.dumps(pv.ig_collabs), **fields)["id"]
        except RuntimeError as exc:  # a private / wrong username makes the whole call fail: post without invites
            collab_note = f"collab invites not sent ({exc})"
            container = _graph("post", f"{uid}/media", **fields)["id"]
    else:
        container = _graph("post", f"{uid}/media", **fields)["id"]
    deadline = time.time() + wait
    while True:
        status = _graph("get", container, fields="status_code,status").get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED") or time.time() > deadline:
            raise RuntimeError(f"Instagram processing {status or 'timed out'}")
        time.sleep(5)
    media_id = _graph("post", f"{uid}/media_publish", creation_id=container)["id"]
    try:
        link = _graph("get", media_id, fields="permalink").get("permalink", "")
    except RuntimeError:
        link = ""
    if collab_note:
        pv.error = collab_note[:500]
        pv.save(update_fields=["error"])
    return media_id, link


def fb_caption(pv, item):
    collabs = " ".join("@" + h for h in pv.ig_collabs)
    return (f"🔥 {pv.title} by {pv.dj.dj_name}\n\n"
            f"🎧 Preview & download on MixMint ({price_text(item)}): {item_url(pv)}\n"
            + (f"\nWith {collabs}\n" if collabs else "")
            + "\nMixMint — home of DJ releases from India's DJs.")[:5000]


def _post_facebook(pv, item, url):
    """Post the rendered promo video to the MixMint Facebook Page (Graph API). Returns (video_id, link)."""
    page_id = settings.FACEBOOK_PAGE_ID
    base = (getattr(settings, "INSTAGRAM_GRAPH_BASE", "") or GRAPH).rstrip("/")
    r = requests.post(f"{base}/{page_id}/videos", timeout=120, data={
        "file_url": url,
        "description": fb_caption(pv, item),
        "access_token": settings.FACEBOOK_PAGE_ACCESS_TOKEN,
    })
    body = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in body:
        raise RuntimeError((body.get("error") or {}).get("message") or f"HTTP {r.status_code}")
    vid = body.get("id", "")
    return vid, (f"https://www.facebook.com/{vid}" if vid else "")


def _yt_token():
    r = requests.post("https://oauth2.googleapis.com/token", timeout=20, data={
        "client_id": settings.YOUTUBE_CLIENT_ID, "client_secret": settings.YOUTUBE_CLIENT_SECRET,
        "refresh_token": settings.YOUTUBE_REFRESH_TOKEN, "grant_type": "refresh_token"})
    tok = r.json().get("access_token") if r.content else None
    if not tok:
        raise RuntimeError(f"Google sign-in failed ({(r.json() if r.content else {}).get('error', r.status_code)}); "
                           "make a new YOUTUBE_REFRESH_TOKEN")
    return tok


def _post_youtube(pv, item):
    tok = _yt_token()
    obj = _r2().client().get_object(Bucket=settings.R2_PUBLIC_BUCKET, Key=pv.output_key)
    size = int(obj["ContentLength"])
    meta = {"snippet": {"title": yt_title(pv), "description": yt_description(pv, item), "categoryId": "10",
                        "tags": ["dj remix", "dj song", "remix", pv.dj.dj_name, "mixmint"]},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
    init = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                         json=meta, timeout=30, headers={"Authorization": f"Bearer {tok}", "X-Upload-Content-Type": "video/mp4",
                                                         "X-Upload-Content-Length": str(size)})
    if init.status_code >= 400 or "Location" not in init.headers:
        raise RuntimeError(_google_err(init))
    up = requests.put(init.headers["Location"], data=obj["Body"].iter_chunks(1024 * 1024), timeout=240,
                      headers={"Authorization": f"Bearer {tok}", "Content-Type": "video/mp4", "Content-Length": str(size)})
    if up.status_code >= 400:
        raise RuntimeError(_google_err(up))
    return up.json()["id"]


def _google_err(r):
    try:
        e = r.json().get("error") or {}
        reason = ((e.get("errors") or [{}])[0]).get("reason", "")
        if reason == "quotaExceeded":
            return "YouTube daily upload limit reached; it'll work again tomorrow."
        return e.get("message") or f"HTTP {r.status_code}"
    except Exception:
        return f"HTTP {r.status_code}"


def asset_channel():
    from . import vault

    return getattr(settings, "TELEGRAM_ASSETS_CHANNEL_ID", "") or vault.channels().get("track") or ""


def _delete(bucket, key):
    if not key:
        return
    try:
        _r2().client().delete_object(Bucket=bucket, Key=key)
    except Exception as exc:
        logger.warning("Promo: couldn't delete %s (%s)", key, type(exc).__name__)


def archive(pv):
    """Keep the finished video in the private Telegram asset channel (admins only). Returns True when stored."""
    if pv.asset_file_id or not pv.output_key:
        return bool(pv.asset_file_id)
    chat = asset_channel()
    if not chat:
        return False
    from . import vault

    try:
        obj = _r2().client().get_object(Bucket=settings.R2_PUBLIC_BUCKET, Key=pv.output_key)
        if int(obj["ContentLength"]) > 49 * 1024 * 1024:  # Bot API upload limit is 50 MB
            return False
        caption = (f"Promo #{pv.pk} · {pv.title} · {pv.dj.dj_name}\n{item_url(pv)}"
                   + (f"\nIG: {pv.ig_url}" if pv.ig_url else "") + (f"\nYT: {yt_url(pv)}" if pv.yt_video_id else ""))
        res, err = vault._call("sendVideo", data={"chat_id": chat, "caption": caption[:1000], "supports_streaming": "true"},
                               files={"video": (f"promo-{pv.pk}.mp4", obj["Body"].read(), "video/mp4")}, timeout=180)
    except Exception as exc:
        logger.error("Promo archive failed for %s (%s)", pv.pk, type(exc).__name__)
        return False
    if not res:
        logger.error("Promo archive failed for %s (%s)", pv.pk, err)
        return False
    media = res.get("video") or res.get("document") or {}
    pv.asset_message_id, pv.asset_file_id = res.get("message_id"), media.get("file_id", "")
    pv.save(update_fields=["asset_message_id", "asset_file_id", "updated_at"])
    return bool(pv.asset_file_id)


def _plain_channel_post(pv):
    """No promo video after all: post the release to the public channel the usual way (cover + buy link)."""
    item = item_for(pv)
    if item is not None:
        from . import bot

        bot.post_release(item, pv.content_type, channel_post=True, tell_dj=False)


def cleanup_cloud(pv):
    _delete(settings.R2_PRIVATE_BUCKET, pv.raw_key)
    _delete(settings.R2_PUBLIC_BUCKET, pv.output_key)
    _delete(settings.R2_PUBLIC_BUCKET, pv.thumb_key)
    pv.output_key = pv.thumb_key = pv.raw_key = ""
    pv.save(update_fields=["output_key", "thumb_key", "raw_key", "updated_at"])


def channel_buttons(pv, item):
    rows = [[{"text": f"🎧 Preview and buy · {price_text(item)}", "url": item_url(pv)}]]
    social = []
    if pv.yt_video_id:
        social.append({"text": "▶ YouTube", "url": yt_url(pv)})
    if pv.ig_url:
        social.append({"text": "📸 Instagram", "url": pv.ig_url})
    if social:
        rows.append(social)
    return {"inline_keyboard": rows}


def _post_channel(pv, item):
    """Public channel post: the video plus MixMint, YouTube and Instagram links."""
    channel = getattr(settings, "TELEGRAM_CHANNEL_ID", "") or ""
    video = pv.asset_file_id or video_url(pv)
    if not channel or not video:
        return
    from . import bot

    lines = [f"🔥 {pv.title} by {pv.dj.dj_name} · {price_text(item)}", "", f"🎧 MixMint: {item_url(pv)}"]
    if pv.yt_video_id:
        lines.append(f"▶ YouTube: {yt_url(pv)}")
    if pv.ig_url:
        lines.append(f"📸 Instagram: {pv.ig_url}")
    res = bot.send_raw({"chat_id": channel, "video": video, "supports_streaming": True, "caption": "\n".join(lines)[:1000],
                        "reply_markup": channel_buttons(pv, item)}, method="sendVideo")
    if res and res.get("message_id"):
        pv.channel_message_id = res["message_id"]
        pv.save(update_fields=["channel_message_id", "updated_at"])


def yt_url(pv):
    return f"https://youtube.com/shorts/{pv.yt_video_id}" if pv.yt_video_id else ""


def _after_publish(pv):
    from . import bot

    links = []
    if pv.ig_url:
        links.append(("Instagram", pv.ig_url))
    if pv.yt_video_id:
        links.append(("YouTube", yt_url(pv)))
    if pv.status == "posted":
        tip = ("\n\nAccept the collab invite in Instagram (notifications, or Profile → ☰ → Collab requests) so the reel "
               "shows on your profile too." if pv.ig_url and pv.ig_collabs else "")
        _dj(pv, f"Your promo for “{pv.title}” is live 🎉 Share it and tag @mixmint.site.{tip}",
                   [links] if links else None)
    msg = f"Promo “{pv.title}”: {pv.status}" + (f" ({pv.error})" if pv.error else "")
    if pv.yt_video_id and pv.yt_collabs:
        msg += ("\n\nYouTube collab invites (YouTube has no API for these): open the video in YouTube Studio → "
                "Collaboration → invite " + ", ".join("@" + h for h in pv.yt_collabs))
        links.append(("Open in YouTube Studio", f"https://studio.youtube.com/video/{pv.yt_video_id}/edit"))
    _admin(msg, [links] if links else None)


def _dj(pv, text, buttons=None):
    """Message the DJ: their linked Telegram, else the chat they sent the clip from."""
    from . import bot

    if bot.notify(pv.dj.profile, text, buttons) is None and pv.tg_chat_id:
        _send(pv.tg_chat_id, text, buttons)


def _admin(text, buttons=None):
    from .support import admin_chat_id

    chat = admin_chat_id()
    if chat:
        try:
            _send(chat, text, buttons)
        except Exception:
            logger.exception("Promo admin alert failed")


def status_lines(dj):
    from .models import PromoVideo

    rows = PromoVideo.objects.filter(dj=dj)[:8]
    return [f"• {p.title}: {p.get_status_display()}" for p in rows]
