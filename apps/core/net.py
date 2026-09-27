"""Single source of truth for the client IP address.

X-Forwarded-For is client-controllable: anything left of the entries appended
by *our own* proxies can be forged. We therefore trust exactly
settings.NUM_PROXIES hops and take the address the outermost trusted proxy saw.

* NUM_PROXIES = 0 (local dev, no proxy)  -> REMOTE_ADDR
* NUM_PROXIES = 1 (Render/Railway/Vercel) -> last XFF entry
* NUM_PROXIES = 2 (Cloudflare -> Render)  -> second-to-last XFF entry
"""

import ipaddress

from django.conf import settings


def _valid(ip):
    try:
        return str(ipaddress.ip_address(ip.strip()))
    except (ValueError, AttributeError):
        return None


def get_client_ip(request):
    remote = _valid(request.META.get("REMOTE_ADDR", "")) or "0.0.0.0"  # nosec B104 - placeholder value, not a bind
    hops = int(getattr(settings, "NUM_PROXIES", 0) or 0)
    if hops <= 0:
        return remote
    xff = [p.strip() for p in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if p.strip()]
    if len(xff) >= hops:
        return _valid(xff[-hops]) or remote
    return _valid(xff[0]) if xff and _valid(xff[0]) else remote
