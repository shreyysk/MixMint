"""SEO: structured data, genre landing pages, sitemap, link previews."""

import json
import re

import pytest
from django.test import Client


def ld(html):
    return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


@pytest.mark.django_db
def test_home_has_site_search_schema():
    blocks = ld(Client().get("/").content.decode())
    graph = blocks[0]["@graph"]
    assert {g["@type"] for g in graph} == {"Organization", "WebSite"}
    assert "search_term_string" in graph[1]["potentialAction"]["target"]


@pytest.mark.django_db
def test_track_page_has_product_with_price(track):
    track.genre = "Tulu"
    track.save()
    html = Client().get(f"/tracks/{track.id}/").content.decode()
    rec = ld(html)[0]["@graph"][0]
    assert rec["offers"]["priceCurrency"] == "INR" and float(rec["offers"]["price"]) == float(track.price)
    assert rec["byArtist"]["name"] == track.dj.dj_name and rec["genre"] == "Tulu"
    assert 'property="og:url"' in html


@pytest.mark.django_db
def test_album_page_has_og_and_schema(album):
    html = Client().get(f"/albums/{album.id}/").content.decode()
    assert f"{album.title} — " in html and ld(html)[0]["@graph"][0]["offers"]["priceCurrency"] == "INR"


@pytest.mark.django_db
def test_genre_landing_and_sitemap(track):
    track.genre = "Tulu"
    track.save()
    c = Client()
    r = c.get("/genre/tulu/")
    page = r.content.decode()
    assert r.status_code == 200 and "Tulu DJ songs, edits &amp; remixes" in page and track.title in page
    assert c.get("/genre/not-a-genre/").status_code == 404
    assert c.get("/sample-packs/").status_code == 200
    sm = c.get("/sitemap.xml").content.decode()
    assert "/genre/tulu/" in sm and "/sample-packs/" in sm
    assert '/genre/kannada/' in c.get("/").content.decode()  # footer links


def test_ld_json_cannot_break_out_of_script():
    from apps.core.seo_utils import ld_json

    assert "</script>" not in ld_json({"name": "</script><b>x"})
