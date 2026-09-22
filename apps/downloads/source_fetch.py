"""
Lazy fetch for DJ backend source files (Google Drive / MediaFire / generic URL).

Strategy: fetch-on-first-download-request -> temp cache on MixMint server ->
stream via our own signed endpoint -> cleanup job deletes cache.

Security: source URL never leaves the server. Only the token URL is public.
"""

import logging
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from django.conf import settings

logger = logging.getLogger("mixmint")

_GDRIVE_ID_PATTERNS = [
    re.compile(r"/file/d/([A-Za-z0-9_-]{10,})"),
    re.compile(r"[?&]id=([A-Za-z0-9_-]{10,})"),
]

_MEDIAFIRE_HINTS = ("mediafire.com",)


def extract_gdrive_id(url):
    for pat in _GDRIVE_ID_PATTERNS:
        m = pat.search(url or "")
        if m:
            return m.group(1)
    return None


def _cache_dir():
    base = Path(settings.MEDIA_ROOT) / getattr(settings, "EXTERNAL_DOWNLOAD_CACHE_DIR", "external_cache")
    base.mkdir(parents=True, exist_ok=True)
    return base


def _check_size_ok(resp):
    max_mb = getattr(settings, "EXTERNAL_DOWNLOAD_MAX_MB", 500)
    length = resp.headers.get("Content-Length")
    if length and length.isdigit():
        if int(length) > max_mb * 1024 * 1024:
            raise ValueError(f"Source file too large (> {max_mb}MB), refusing to cache.")


def _stream_to_file(resp, dest, timeout_note=""):
    max_mb = getattr(settings, "EXTERNAL_DOWNLOAD_MAX_MB", 500)
    written = 0
    with open(dest, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=1024 * 256):
            if not chunk:
                continue
            written += len(chunk)
            if written > max_mb * 1024 * 1024:
                fh.close()
                try:
                    os.remove(dest)
                except OSError:
                    pass
                raise ValueError(f"Source file too large (> {max_mb}MB), refusing to cache. {timeout_note}")
            fh.write(chunk)
    return dest


def fetch_gdrive(url, dest_name):
    """Fetch a Drive file server-side.

    Preferred: Drive API v3 with API key (public files) — set GOOGLE_DRIVE_API_KEY.
    Fallback: direct `uc?export=download` stream with confirm-token handling.
    DJ must share the file publicly or with the service account email.
    """
    file_id = extract_gdrive_id(url)
    if not file_id:
        raise ValueError("Could not parse Google Drive file ID from source URL.")
    timeout = getattr(settings, "EXTERNAL_DOWNLOAD_TIMEOUT_SEC", 120)
    dest = str(_cache_dir() / dest_name)
    session = requests.Session()

    api_key = getattr(settings, "GOOGLE_DRIVE_API_KEY", "") or ""
    if api_key:
        api_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={api_key}"
        resp = session.get(api_url, stream=True, timeout=timeout)
        if resp.status_code == 200:
            _check_size_ok(resp)
            return _stream_to_file(resp, dest)
        logger.warning("Drive API download failed (%s), falling back to uc endpoint.", resp.status_code)

    # Fallback: export/download endpoint with large-file confirm token.
    # NOTE: only read resp.text when the response is HTML; reading .text on a
    # streamed binary body would consume the stream.
    dl_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    resp = session.get(dl_url, stream=True, timeout=timeout)
    for _ in range(3):
        ctype = resp.headers.get("Content-Type", "")
        if "text/html" not in ctype:
            break
        page = resp.text[:8000]
        confirm = None
        for k, v in resp.cookies.items():
            if k.startswith("download_warning"):
                confirm = v
                break
        if not confirm:
            m = re.search(r"confirm=([0-9A-Za-z_-]+)", page)
            confirm = m.group(1) if m else None
        if not confirm:
            break
        resp = session.get(f"{dl_url}&confirm={confirm}", stream=True, timeout=timeout)
    if resp.status_code != 200:
        raise ValueError(f"Google Drive fetch failed (HTTP {resp.status_code}).")
    ctype = resp.headers.get("Content-Type", "")
    if "text/html" in ctype:
        raise ValueError("Google Drive returned an HTML page (not shared publicly or virus-scan block).")
    _check_size_ok(resp)
    return _stream_to_file(resp, dest)


def fetch_mediafire(url, dest_name):
    """Best-effort MediaFire fetch.

    MediaFire has no robust free official API for server-side pulls; their pages
    use JS redirects + rotating tokens and automated scraping is fragile (and may
    breach their ToS). Prefer Google Drive as the backend source. This helper
    attempts a direct-link resolve but raises a clear error when it cannot.
    """
    logger.warning(
        "MediaFire source requested — best-effort only; prefer Google Drive. URL host: %s",
        urlparse(url or "").netloc,
    )
    timeout = getattr(settings, "EXTERNAL_DOWNLOAD_TIMEOUT_SEC", 120)
    dest = str(_cache_dir() / dest_name)
    try:
        resp = requests.get(url, stream=True, timeout=timeout, headers={"User-Agent": "MixMint/2.0 (server fetch)"})
    except Exception as exc:
        raise ValueError(f"MediaFire fetch failed: {exc}") from exc
    ctype = resp.headers.get("Content-Type", "")
    if "text/html" in ctype:
        # Try to find a direct download anchor in the page.
        m = re.search(r'href="(https://download[^"]+)"', resp.text or "")
        if not m:
            raise ValueError(
                "MediaFire page did not yield a direct file link. "
                "Please use a Google Drive link as the backend source instead."
            )
        direct = m.group(1)
        resp = requests.get(direct, stream=True, timeout=timeout, headers={"User-Agent": "MixMint/2.0 (server fetch)"})
        if resp.status_code != 200 or "text/html" in resp.headers.get("Content-Type", ""):
            raise ValueError("MediaFire direct link expired or blocked. Use a Google Drive link instead.")
    if resp.status_code != 200:
        raise ValueError(f"MediaFire fetch failed (HTTP {resp.status_code}).")
    _check_size_ok(resp)
    return _stream_to_file(resp, dest)


def fetch_generic(url, dest_name):
    timeout = getattr(settings, "EXTERNAL_DOWNLOAD_TIMEOUT_SEC", 120)
    dest = str(_cache_dir() / dest_name)
    resp = requests.get(url, stream=True, timeout=timeout, headers={"User-Agent": "MixMint/2.0 (server fetch)"})
    if resp.status_code != 200:
        raise ValueError(f"Source fetch failed (HTTP {resp.status_code}).")
    _check_size_ok(resp)
    return _stream_to_file(resp, dest)


def probe_source(source_url, timeout=None):
    """Lightweight pre-check before a DJ link is accepted.

    Returns (ok, info): ok=True with size info, or ok=False with a plain-language
    reason + how-to-fix guide hint. Never downloads the whole file.
    """
    url = (source_url or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        return False, "Link must start with http:// or https://."
    timeout = timeout or getattr(settings, "EXTERNAL_DOWNLOAD_TIMEOUT_SEC", 120)
    host = urlparse(url).netloc.lower()
    if "drive.google.com" in host and not extract_gdrive_id(url):
        return (
            False,
            "This Google Drive link has no file ID. Open the file in Drive → Share → "
            "'Anyone with the link (Viewer)' → copy the /file/d/... link and paste it.",
        )
    try:
        resp = requests.head(url, timeout=15, allow_redirects=True, headers={"User-Agent": "MixMint/2.0 (link-check)"})
        if resp.status_code >= 400:
            resp = requests.get(
                url,
                timeout=20,
                stream=True,
                headers={"User-Agent": "MixMint/2.0 (link-check)", "Range": "bytes=0-1023"},
            )
        if resp.status_code >= 400:
            return (
                False,
                f"Link returned HTTP {resp.status_code}. For Drive: Share → 'Anyone with the link (Viewer)'. "
                "For MediaFire/direct links: make sure the link opens without login.",
            )
        length = resp.headers.get("Content-Length")
        max_mb = getattr(settings, "EXTERNAL_DOWNLOAD_MAX_MB", 500)
        if length and length.isdigit() and int(length) > max_mb * 1024 * 1024:
            return False, f"File is larger than our {max_mb}MB per-track limit."
        if length and length.isdigit():
            mb = int(length) / (1024 * 1024)
            return True, f"Link OK — file reachable (~{mb:.1f} MB). It will be cached to MixMint on first download."
        return True, "Link OK — file reachable. It will be cached to MixMint on first download."
    except Exception as exc:
        return False, f"Could not reach the link ({exc}). Check sharing: Drive → 'Anyone with the link (Viewer)'."


def fetch_from_source(source_url, source_type, dest_name):
    """Fetch backend file to local temp cache. Returns absolute local path."""
    if not source_url:
        raise ValueError("No backend source URL configured for this track.")
    st = (source_type or "other").lower()
    host = urlparse(source_url).netloc.lower()
    if st == "gdrive" or "drive.google.com" in host:
        return fetch_gdrive(source_url, dest_name)
    if st == "mediafire" or any(h in host for h in _MEDIAFIRE_HINTS):
        return fetch_mediafire(source_url, dest_name)
    return fetch_generic(source_url, dest_name)
