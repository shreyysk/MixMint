"""Promo videos: upload choice → Telegram/web clip → render job → approval → Instagram (collabs) + YouTube +
Telegram channel (with links) → video kept in the private asset channel, removed from R2."""

import json
import time
from unittest import mock

import boto3
import pytest
from django.test import Client, override_settings
from moto import mock_aws

from apps.admin_panel import promo
from apps.admin_panel.models import PromoVideo
from apps.admin_panel.support import handle_update

ADMIN = "999"
R2 = dict(AWS_ACCESS_KEY_ID="t", AWS_SECRET_ACCESS_KEY="t", AWS_S3_ENDPOINT_URL="https://acct.r2.cloudflarestorage.com",
          R2_PRIVATE_BUCKET="raw", R2_PUBLIC_BUCKET="pub", R2_PUBLIC_URL="https://cdn.example.com")


@pytest.fixture
def s3():
    with mock_aws(), override_settings(**R2):
        c = boto3.client("s3", region_name="us-east-1")
        c.create_bucket(Bucket="raw")
        c.create_bucket(Bucket="pub")
        with mock.patch("apps.core.r2.client", lambda: c):
            yield c


@pytest.fixture
def tg(settings):
    settings.TELEGRAM_BOT_TOKEN = "123:abc"
    settings.TELEGRAM_ADMIN_CHAT_ID = ADMIN
    settings.TELEGRAM_BOT_USERNAME = "mixmint_bot"
    settings.TELEGRAM_CHANNEL_ID = "@mixmint_releases"
    settings.TELEGRAM_ASSETS_CHANNEL_ID = "-100777"
    settings.BASE_URL = "https://mixmint.site"
    calls = []

    def fake(method, payload):
        calls.append((method, payload))
        if method == "getFile":
            return {"file_path": "videos/clip.mp4"}
        return {"message_id": len(calls)}

    with mock.patch("apps.admin_panel.support.tg", side_effect=fake):
        yield calls


def sent(calls, chat, method=None):
    return [p for m, p in calls if str(p.get("chat_id")) == str(chat) and (method is None or m == method)]


def text_of(p):
    return p.get("text") or p.get("caption") or ""


@pytest.fixture
def pv(dj_user, track):
    return promo.create(track, "track", ig="@djtest, featured.dj", yt="@TestDJChannel", template="bold")


# ─────────────────────────────── collab handles ───────────────────────────────
def test_handles_are_cleaned_and_capped():
    assert promo.clean_handles("@a, b https://instagram.com/c/ @A mixmint d e", "ig") == ["a", "b", "c"]
    assert len(promo.clean_handles(" ".join(f"ch{i}x" for i in range(15)), "yt")) == promo.YT_MAX == 10
    assert promo.IG_MAX == 3
    assert "up to 3" in promo.handle_errors("a b c d", "ig")
    assert promo.handle_errors("a b c", "ig") == ""
    assert "valid" in promo.handle_errors("bad!name", "ig")
    assert promo.handle_errors("https://www.youtube.com/@my.chan", "yt") == ""


# ─────────────────────────────── upload form ───────────────────────────────
@pytest.mark.django_db
def test_upload_with_promo_goes_to_promo_page(dj_user, s3, tg):
    u, dj = dj_user
    s3.put_object(Bucket="raw", Key=f"tracks/{dj.id}/abc-song.mp3", Body=b"x" * 2048)
    c = Client()
    c.force_login(u)
    base = {"kind": "track", "title": "Midnight", "price": "99", "file_key": f"tracks/{dj.id}/abc-song.mp3",
            "youtube_url": "https://youtu.be/dQw4w9WgXcQ", "content_responsibility_accepted": "on"}
    with mock.patch("apps.accounts.upload_views._tag_track"):
        r = c.post("/upload/", {**base, "promo_wanted": "on", "promo_ig": "a b c d", "promo_rights": "on"})
        assert r.status_code == 400 and not PromoVideo.objects.exists()  # 4 > Instagram's 3
        r = c.post("/upload/", {**base, "promo_wanted": "on", "promo_ig": "a b"})
        assert r.status_code == 400  # rights box
        r = c.post("/upload/", {**base, "promo_wanted": "on", "promo_ig": "@me, @guest", "promo_yt": "@mychan",
                                "promo_rights": "on", "promo_template": "clean"})
    p = PromoVideo.objects.get()
    assert r.status_code == 302 and r["Location"] == f"/dashboard/promo/{p.pk}/"
    assert p.ig_collabs == ["me", "guest"] and p.yt_collabs == ["mychan"] and p.template == "clean" and p.status == "waiting"
    assert not sent(tg, "@mixmint_releases")  # channel post waits for the video
    page = c.get(r["Location"])
    assert page.status_code == 200 and b"Send in Telegram" in page.content and b"start=pv_" in page.content
    other = Client()
    other.force_login(__import__("apps.accounts.models", fromlist=["User"]).User.objects.create_user(email="x@y.z", password="Pw12345!x"))
    assert other.get(r["Location"]).status_code == 404


# ─────────────────────────────── Telegram clip ───────────────────────────────
@pytest.mark.django_db
def test_telegram_start_link_and_video(pv, s3, tg, settings):
    handle_update({"message": {"chat": {"id": 555, "type": "private"}, "text": f"/start {promo.start_payload(pv)}"}})
    pv.refresh_from_db()
    assert pv.tg_chat_id == "555" and "Send me the promo video" in text_of(sent(tg, 555)[0])
    big = {"message": {"chat": {"id": 555, "type": "private"}, "video": {"file_id": "F", "file_size": 30 * 1024 * 1024}}}
    handle_update(big)
    assert "20 MB" in text_of(sent(tg, 555)[-1])
    resp = mock.Mock(content=b"VID", status_code=200)
    resp.raise_for_status = lambda: None
    with mock.patch("apps.admin_panel.promo.requests.get", return_value=resp), \
         mock.patch("apps.admin_panel.promo.start_render", return_value=True) as render:
        handle_update({"message": {"chat": {"id": 555, "type": "private"}, "video": {"file_id": "F", "file_size": 1000}}})
    pv.refresh_from_db()
    assert pv.status == "received" and pv.source == "telegram" and render.called
    assert s3.get_object(Bucket="raw", Key=pv.raw_key)["Body"].read() == b"VID"


@pytest.mark.django_db
def test_expired_or_forged_promo_link(pv, tg):
    payload = promo.start_payload(pv)
    with mock.patch("apps.admin_panel.promo.time.time", return_value=time.time() + promo.LINK_TTL + 10):
        assert promo.from_payload(payload) is None
    assert promo.from_payload(payload[:-1] + ("0" if payload[-1] != "0" else "1")) is None
    assert promo.from_payload(payload) == pv


@pytest.mark.django_db
def test_stray_video_explains(tg, user):
    handle_update({"message": {"chat": {"id": 8, "type": "private"}, "video": {"file_id": "F", "file_size": 10}}})
    assert "Free promo" in text_of(sent(tg, 8)[0])


# ─────────────────────────────── render job ───────────────────────────────
@pytest.mark.django_db
def test_render_dispatch_job_and_done(pv, s3, tg, settings):
    settings.PROMO_GITHUB_REPO, settings.PROMO_GITHUB_TOKEN = "me/repo", "tok"
    s3.put_object(Bucket="raw", Key=f"promo/{pv.dj_id}/{pv.pk}-1-raw.mp4", Body=b"v")
    with mock.patch("apps.admin_panel.promo.requests.post", return_value=mock.Mock(status_code=204)) as post:
        promo.web_uploaded(pv, f"promo/{pv.dj_id}/{pv.pk}-1-raw.mp4")
    body = post.call_args.kwargs["json"]
    assert post.call_args.args[0] == "https://api.github.com/repos/me/repo/dispatches" and body["event_type"] == "promo_render"
    pv.refresh_from_db()
    assert pv.status == "rendering"
    c = Client()
    job_url = body["client_payload"]["job_url"].replace("https://mixmint.site", "")
    done_url = body["client_payload"]["done_url"].replace("https://mixmint.site", "")
    assert c.get(job_url.split("?")[0] + "?t=1.bad").status_code == 403
    job = c.get(job_url).json()
    assert job["template"] == "bold" and job["dj"] == "Test DJ" and job["price"] == "₹100" and job["max_seconds"] == 59
    s3.put_object(Bucket="pub", Key=job["output"]["key"], Body=b"mp4")
    s3.put_object(Bucket="pub", Key=job["thumb"]["key"], Body=b"jpg")
    r = c.post(done_url, data=json.dumps({"ok": True, "output_key": job["output"]["key"], "thumb_key": job["thumb"]["key"], "duration": 21.5}),
               content_type="application/json")
    assert r.status_code == 200
    pv.refresh_from_db()
    assert pv.status == "review" and pv.duration == 21.5
    with pytest.raises(Exception):
        s3.head_object(Bucket="raw", Key=f"promo/{pv.dj_id}/{pv.pk}-1-raw.mp4")  # original removed from R2
    admin = sent(tg, ADMIN, "sendVideo")[0]
    cb = [b["callback_data"] for row in admin["reply_markup"]["inline_keyboard"] for b in row if "callback_data" in b]
    assert cb == [f"pvok:{pv.pk}", f"pvno:{pv.pk}"] and "@djtest" in admin["caption"]


@pytest.mark.django_db
def test_renderer_not_connected_tells_admin(pv, tg, settings):
    settings.PROMO_GITHUB_REPO = ""
    assert promo.start_render(pv) is False
    assert "renderer" in text_of(sent(tg, ADMIN)[0])


# ─────────────────────────────── approval, cap, publish ───────────────────────────────
def _ready(pv, s3):
    pv.output_key, pv.thumb_key, pv.status = f"promo/{pv.dj_id}/{pv.pk}-9.mp4", f"promo/{pv.dj_id}/{pv.pk}-9.jpg", "review"
    pv.save()
    s3.put_object(Bucket="pub", Key=pv.output_key, Body=b"m" * 100)
    s3.put_object(Bucket="pub", Key=pv.thumb_key, Body=b"j")


@pytest.mark.django_db
def test_daily_cap_queues_then_releases(pv, s3, tg):
    _ready(pv, s3)
    promo.save_cfg(daily_cap=1)
    PromoVideo.objects.create(dj=pv.dj, content_type="album", content_id=1, title="x", status="posted")
    with mock.patch("apps.admin_panel.promo.trigger_publish") as trig:
        handle_update({"callback_query": {"id": "1", "data": f"pvok:{pv.pk}", "message": {"chat": {"id": ADMIN}}}})
        pv.refresh_from_db()
        assert pv.status == "queued" and not trig.called and "tomorrow" in text_of(sent(tg, ADMIN)[-1])
        PromoVideo.objects.filter(content_type="album").update(updated_at="2020-01-01T00:00:00Z")
        assert promo.release_queue() == 1
        pv.refresh_from_db()
        assert pv.status == "posting" and trig.called


@pytest.mark.django_db
def test_only_admin_can_approve(pv, s3, tg):
    _ready(pv, s3)
    handle_update({"callback_query": {"id": "1", "data": f"pvok:{pv.pk}", "message": {"chat": {"id": 12345}}}})
    pv.refresh_from_db()
    assert pv.status == "review"


@pytest.mark.django_db
def test_publish_instagram_collab_youtube_channel_and_archive(pv, s3, tg, settings, dj_user):
    from apps.admin_panel.models import TelegramLink

    TelegramLink.objects.create(profile=pv.dj.profile, chat_id="321")
    settings.INSTAGRAM_USER_ID, settings.INSTAGRAM_ACCESS_TOKEN = "17841", "IGT"
    settings.YOUTUBE_CLIENT_ID = settings.YOUTUBE_CLIENT_SECRET = settings.YOUTUBE_REFRESH_TOKEN = "y"
    _ready(pv, s3)
    pv.status = "posting"
    pv.save()
    graph_calls = []

    def graph(method, path, **data):
        graph_calls.append((method, path, data))
        if path.endswith("/media"):
            return {"id": "C1"}
        if path == "C1":
            return {"status_code": "FINISHED"}
        if path.endswith("/media_publish"):
            return {"id": "M1"}
        return {"permalink": "https://www.instagram.com/reel/XYZ/"}

    vault_res = ({"message_id": 50, "video": {"file_id": "ASSET1"}}, "")
    with mock.patch("apps.admin_panel.promo._graph", side_effect=graph), \
         mock.patch("apps.admin_panel.promo._post_youtube", return_value="yt123") as yt, \
         mock.patch("apps.admin_panel.vault._call", return_value=vault_res) as vcall:
        assert promo.publish(pv) == "posted"
    create = graph_calls[0][2]
    assert json.loads(create["collaborators"]) == ["djtest", "featured.dj"] and create["media_type"] == "REELS"
    assert create["cover_url"].startswith("https://cdn.example.com/promo/")
    assert vcall.call_args.kwargs["data"]["chat_id"] == "-100777"
    pv.refresh_from_db()
    assert pv.ig_url.endswith("/XYZ/") and pv.yt_video_id == "yt123" and pv.asset_file_id == "ASSET1"
    assert pv.output_key == "" and pv.thumb_key == ""  # removed from R2 once safe in Telegram
    post = sent(tg, "@mixmint_releases", "sendVideo")[0]
    assert post["video"] == "ASSET1"
    urls = [b["url"] for row in post["reply_markup"]["inline_keyboard"] for b in row]
    assert urls == [promo.item_url(pv), "https://youtube.com/shorts/yt123", "https://www.instagram.com/reel/XYZ/"]
    assert "YouTube:" in post["caption"] and "Instagram:" in post["caption"] and "mixmint.site/tracks/" in post["caption"]
    assert "Collab requests" in text_of(sent(tg, 321)[-1])
    admin = text_of(sent(tg, ADMIN)[-1])
    assert "YouTube Studio" in admin and "@TestDJChannel" in admin


@pytest.mark.django_db
def test_instagram_bad_collab_still_posts(pv, s3, tg, settings):
    settings.INSTAGRAM_USER_ID, settings.INSTAGRAM_ACCESS_TOKEN = "1", "T"
    _ready(pv, s3)
    calls = []

    def graph(method, path, **data):
        calls.append(data)
        if path.endswith("/media") and "collaborators" in data:
            raise RuntimeError("Invalid user")
        return {"id": "C"} if path.endswith("/media") else {"status_code": "FINISHED"} if path == "C" else {"id": "M", "permalink": "p"}

    with mock.patch("apps.admin_panel.promo._graph", side_effect=graph):
        mid, _ = promo._post_instagram(pv, None, "https://cdn.example.com/x.mp4")
    pv.refresh_from_db()
    assert mid == "M" and "collab invites not sent" in pv.error


@pytest.mark.django_db
def test_reject_posts_plain_release_and_cleans_up(pv, s3, tg):
    _ready(pv, s3)
    with mock.patch("apps.admin_panel.vault._call", return_value=({"message_id": 1, "video": {"file_id": "A"}}, "")):
        handle_update({"callback_query": {"id": "1", "data": f"pvno:{pv.pk}", "message": {"chat": {"id": ADMIN}}}})
    pv.refresh_from_db()
    assert pv.status == "rejected" and pv.output_key == ""
    assert sent(tg, "@mixmint_releases")  # the release still gets its normal channel post


@pytest.mark.django_db
def test_run_endpoint_is_signed(pv, client):
    pv.status = "posting"
    pv.save()
    assert client.post("/promo/run/", data=json.dumps({"id": pv.pk}), content_type="application/json",
                       HTTP_X_PROMO_SIG="nope").status_code == 403
    with mock.patch("apps.admin_panel.promo.publish", return_value="posted") as pub:
        r = client.post("/promo/run/", data=json.dumps({"id": pv.pk}), content_type="application/json",
                        HTTP_X_PROMO_SIG=promo.run_sig(pv.pk))
    assert r.json()["status"] == "posted" and pub.called


@pytest.mark.django_db
def test_youtube_text(pv):
    assert pv.title in promo.yt_title(pv) and "#shorts" in promo.yt_title(pv) and len(promo.yt_title(pv)) <= 100
    d = promo.yt_description(pv, None)
    assert "@TestDJChannel" in d and "/tracks/" in d


@pytest.mark.django_db
def test_admin_settings_card(admin_user, pv):
    c = Client()
    c.force_login(admin_user)
    r = c.get("/api/v1/admin/settings/")
    assert r.status_code == 200 and b"Promo videos" in r.content and b"Test Track" in r.content
    r = c.post("/api/v1/admin/settings/", {"action": "promo", "enabled": "on", "daily_cap": "3"})
    assert promo.cfg()["daily_cap"] == 3 and promo.cfg()["auto_approve"] is False


@pytest.mark.django_db
def test_quick_search(client, track):
    r = client.get("/search/quick/?q=test")
    titles = [x["title"] for x in r.json()["results"]]
    assert "Test Track" in titles and "Test DJ" in titles
    assert client.get("/search/quick/?q=a").json()["results"] == []
