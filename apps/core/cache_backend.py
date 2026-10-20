"""Redis cache with a tiny in-process layer for site-wide settings.

Every page reads a handful of site-wide values (maintenance mode, IP blacklist, payment test mode,
gateway label, site settings). On Vercel each Redis read is a network round trip, so a page paid
5-9 sequential round trips before rendering. These keys change rarely, so each server instance keeps
its own copy for a few seconds. Writes and deletes made by this instance clear the local copy at
once; other instances pick up a change within LOCAL_TTL seconds.
"""

import logging
import threading
import time

from django.core.cache.backends.redis import RedisCache

logger = logging.getLogger("mixmint")
_last_warn = [0.0]


def _warn(op, exc):
    # Redis down or over its quota: log at most once a minute, never break the page.
    now = time.monotonic()
    if now - _last_warn[0] > 60:
        _last_warn[0] = now
        logger.error("Cache %s failed (%s); serving without the cache", op, exc.__class__.__name__)

HOT_KEYS = frozenset({
    "platform_mode",
    "ip_blacklist",
    "payments_test_mode",
    "payment_gateway_label",
    "global_settings_ctx",
})
LOCAL_TTL = 10  # seconds


class LayeredRedisCache(RedisCache):
    """Also fail-safe: if Redis is unreachable or over quota, reads miss and writes are skipped
    instead of raising, so pages keep working (just without caching) under heavy load."""

    def __init__(self, server, params):
        super().__init__(server, params)
        self._local = {}
        self._lock = threading.Lock()

    def _local_get(self, key):
        hit = self._local.get(key)
        if hit and hit[0] > time.monotonic():
            return True, hit[1]
        return False, None

    def _local_put(self, key, value, timeout=None):
        ttl = LOCAL_TTL if timeout is None else min(LOCAL_TTL, timeout)
        if ttl and ttl > 0:
            with self._lock:
                self._local[key] = (time.monotonic() + ttl, value)

    def _local_drop(self, *keys):
        with self._lock:
            for k in keys:
                self._local.pop(k, None)

    def get(self, key, default=None, version=None):
        if key in HOT_KEYS:
            found, value = self._local_get(key)
            if found:
                return value
            value = self._safe("get", default, super().get, key, default, version)
            if value is not default and value is not None:
                self._local_put(key, value)
            return value
        return self._safe("get", default, super().get, key, default, version)

    def _safe(self, op, fallback, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # redis.ConnectionError, TimeoutError, quota errors, ...
            _warn(op, exc)
            return fallback

    def add(self, key, value, timeout=300, version=None):
        return self._safe("add", True, super().add, key, value, timeout, version)

    def incr(self, key, delta=1, version=None):
        try:
            return super().incr(key, delta, version)
        except ValueError:
            raise  # missing key: Django's normal contract
        except Exception as exc:
            _warn("incr", exc)
            return delta

    def get_many(self, keys, version=None):
        return self._safe("get_many", {}, super().get_many, keys, version)

    def set_many(self, data, timeout=300, version=None):
        return self._safe("set_many", [], super().set_many, data, timeout, version)

    def touch(self, key, timeout=300, version=None):
        return self._safe("touch", False, super().touch, key, timeout, version)

    def has_key(self, key, version=None):
        return self._safe("has_key", False, super().has_key, key, version)

    def set(self, key, value, timeout=300, version=None):
        result = self._safe("set", None, super().set, key, value, timeout, version)
        if key in HOT_KEYS:
            self._local_put(key, value, timeout if isinstance(timeout, (int, float)) else None)
        return result

    def delete(self, key, version=None):
        if key in HOT_KEYS:
            self._local_drop(key)
        return self._safe("delete", False, super().delete, key, version)

    def delete_many(self, keys, version=None):
        self._local_drop(*[k for k in keys if k in HOT_KEYS])
        return self._safe("delete_many", None, super().delete_many, keys, version)

    def clear(self):
        with self._lock:
            self._local.clear()
        return self._safe("clear", None, super().clear)
