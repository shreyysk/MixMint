#!/usr/bin/env python3
"""
Walk a MixMint site as a logged-out visitor and flag anything broken.

    python scripts/site_check.py                      # https://mixmint.site
    python scripts/site_check.py http://127.0.0.1:8000 --max 400 --slow 1.5

Checks every same-site page reachable from the home page (links, plus sitemap.xml):
  * status is not 200/301/302 (404s, 500s)                       → BROKEN
  * redirect loops or redirects to another site                   → BROKEN
  * page took longer than --slow seconds                          → SLOW
  * no <title>, or an empty one                                   → WARN
  * images / scripts / stylesheets on the page that fail to load  → BROKEN
Exits with code 1 when anything is BROKEN, so it can run in CI or on a schedule.
Only standard-library Python; no login, no forms submitted, nothing bought.
"""

import argparse
import sys
import time
import urllib.error
import urllib.request
from collections import deque
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlsplit

SKIP_PREFIXES = ("/logout", "/api/", "/admin", "/cron/", "/telegram/", "/vault/", "/checkout/", "/recover/",
                 "/download", "/accounts/google", "/static/admin")
UA = "MixMint-site-check/1.0 (+https://mixmint.site)"


class _Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.assets, self.title, self._in_title = set(), set(), "", False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.links.add(a["href"])
        elif tag in ("img", "script") and a.get("src"):
            self.assets.add(a["src"])
        elif tag == "link" and a.get("href") and (a.get("rel") or "") in ("stylesheet", "icon", "manifest"):
            self.assets.add(a["href"])
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def fetch(url, method="GET", timeout=20):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    t = time.monotonic()
    try:
        resp = _opener.open(req, timeout=timeout)
        body = resp.read() if method == "GET" else b""
        return resp.status, resp.headers, body, time.monotonic() - t
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read() if method == "GET" else b"", time.monotonic() - t
    except Exception as e:  # noqa: BLE001
        return 0, {}, str(e).encode(), time.monotonic() - t


def same_site(url, base):
    return urlsplit(url).netloc == urlsplit(base).netloc


def wanted(url, base):
    if not same_site(url, base):
        return False
    path = urlsplit(url).path
    return not any(path.startswith(p) for p in SKIP_PREFIXES)


def sitemap_urls(base):
    status, _, body, _ = fetch(base + "/sitemap.xml")
    if status != 200:
        return []
    import re

    return re.findall(rb"<loc>([^<]+)</loc>", body)


def run(base, max_pages, slow, own_assets_only=False):
    base = base.rstrip("/")
    queue, seen, asset_seen = deque([base + "/"]), set(), {}
    for u in sitemap_urls(base):
        queue.append(u.decode().strip().replace("https://mixmint.site", base) if "127.0.0.1" in base or "localhost" in base else u.decode().strip())
    problems, pages, bad_assets = [], 0, {}
    while queue and pages < max_pages:
        url = urldefrag(queue.popleft())[0]
        if url in seen or not wanted(url, base):
            continue
        seen.add(url)
        status, headers, body, took = fetch(url)
        pages += 1
        path = urlsplit(url).path or "/"
        if status in (301, 302, 303, 307, 308):
            loc = urljoin(url, headers.get("Location", ""))
            if not same_site(loc, base):
                problems.append(("BROKEN", path, f"redirects off-site to {loc}"))
            elif loc not in seen:
                queue.append(loc)
            continue
        if status != 200:
            problems.append(("BROKEN", path, f"HTTP {status or 'no response'}"))
            continue
        if took > slow:
            problems.append(("SLOW", path, f"{took:.1f}s"))
        if "text/html" not in (headers.get("Content-Type") or ""):
            continue
        page = _Page()
        try:
            page.feed(body.decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001
            problems.append(("WARN", path, "HTML could not be parsed"))
            continue
        if not page.title.strip():
            problems.append(("WARN", path, "no <title>"))
        for href in page.links:
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            nxt = urljoin(url, href)
            if wanted(nxt, base) and nxt not in seen:
                queue.append(nxt)
        for src in page.assets:
            a = urljoin(url, src)
            if a.startswith("data:") or not a.startswith("http") or (own_assets_only and not same_site(a, base)):
                continue
            if a not in asset_seen:
                s, _, _, _ = fetch(a, method="GET" if same_site(a, base) else "HEAD", timeout=15)
                if s in (301, 302, 303, 307, 308):
                    s = 200
                if s == 405:  # some CDNs refuse HEAD
                    s, _, _, _ = fetch(a)
                asset_seen[a] = s
            if asset_seen[a] not in (200, 204, 304):
                bad_assets.setdefault(a, []).append(path)
    for a, on in bad_assets.items():  # one line per broken file, not one per page
        problems.append(("BROKEN", on[0], f"file {a} → HTTP {asset_seen[a] or 'no response'} (used on {len(on)} page(s))"))
    return pages, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("base", nargs="?", default="https://mixmint.site")
    ap.add_argument("--max", type=int, default=300, help="most pages to visit (default 300)")
    ap.add_argument("--slow", type=float, default=2.0, help="seconds before a page counts as slow")
    ap.add_argument("--own-assets-only", action="store_true", help="skip fonts/CDN files on other sites")
    args = ap.parse_args()
    pages, problems = run(args.base, args.max, args.slow, args.own_assets_only)
    order = {"BROKEN": 0, "SLOW": 1, "WARN": 2}
    for kind, path, msg in sorted(set(problems), key=lambda p: (order[p[0]], p[1])):
        print(f"{kind:6} {path}  {msg}")
    broken = sum(1 for p in problems if p[0] == "BROKEN")
    print(f"\nChecked {pages} pages: {broken} broken, "
          f"{sum(1 for p in problems if p[0] == 'SLOW')} slow, {sum(1 for p in problems if p[0] == 'WARN')} warnings.")
    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
