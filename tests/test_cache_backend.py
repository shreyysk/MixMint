"""The layered Redis cache serves hot site-wide keys from memory and forgets them on write/delete."""

from unittest import mock

from apps.core import cache_backend
from apps.core.cache_backend import LayeredRedisCache


def make():
    return LayeredRedisCache("redis://127.0.0.1:1/0", {})


def test_hot_key_read_once_then_local():
    c = make()
    with mock.patch("django.core.cache.backends.redis.RedisCache.get", return_value={"a": 1}) as g:
        assert c.get("global_settings_ctx") == {"a": 1}
        assert c.get("global_settings_ctx") == {"a": 1}
    assert g.call_count == 1


def test_other_keys_always_go_to_redis():
    c = make()
    with mock.patch("django.core.cache.backends.redis.RedisCache.get", return_value=5) as g:
        c.get("rate_limit_x")
        c.get("rate_limit_x")
    assert g.call_count == 2


def test_delete_and_set_refresh_local_copy():
    c = make()
    with mock.patch("django.core.cache.backends.redis.RedisCache.set"), \
            mock.patch("django.core.cache.backends.redis.RedisCache.delete"), \
            mock.patch("django.core.cache.backends.redis.RedisCache.get", return_value=None) as g:
        c.set("platform_mode", "live", 15)
        assert c.get("platform_mode") == "live" and g.call_count == 0
        c.delete("platform_mode")
        assert c.get("platform_mode") is None and g.call_count == 1


def test_local_copy_expires(monkeypatch):
    c = make()
    monkeypatch.setattr(cache_backend, "LOCAL_TTL", 0)
    with mock.patch("django.core.cache.backends.redis.RedisCache.get", return_value="x") as g:
        c.get("ip_blacklist")
        c.get("ip_blacklist")
    assert g.call_count == 2
