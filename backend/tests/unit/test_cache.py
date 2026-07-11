from __future__ import annotations

import pytest

from app.cache.invalidation import CacheInvalidator
from app.cache.memory import MemoryCache
from app.cache.namespaces import CacheNamespace, NamespaceManager
from app.cache.ttl import TTLCache


class TestMemoryCache:
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        cache = MemoryCache()
        await cache.set("key", "value")
        assert await cache.get("key") == "value"

    @pytest.mark.asyncio
    async def test_get_missing(self):
        cache = MemoryCache()
        assert await cache.get("nonexistent") is None

    @pytest.mark.asyncio
    async def test_delete(self):
        cache = MemoryCache()
        await cache.set("key", "value")
        assert await cache.delete("key") is True
        assert await cache.get("key") is None

    @pytest.mark.asyncio
    async def test_delete_missing(self):
        cache = MemoryCache()
        assert await cache.delete("nonexistent") is False

    @pytest.mark.asyncio
    async def test_exists(self):
        cache = MemoryCache()
        await cache.set("key", "value")
        assert await cache.exists("key") is True
        assert await cache.exists("other") is False

    @pytest.mark.asyncio
    async def test_size(self):
        cache = MemoryCache()
        assert await cache.size() == 0
        await cache.set("k1", "v1")
        await cache.set("k2", "v2")
        assert await cache.size() == 2

    @pytest.mark.asyncio
    async def test_clear(self):
        cache = MemoryCache()
        await cache.set("k1", "v1")
        await cache.clear()
        assert await cache.size() == 0

    @pytest.mark.asyncio
    async def test_ttl_expiry(self):
        cache = MemoryCache()
        import time
        cache._expiry["key"] = time.time() - 1
        cache._store["key"] = "value"
        cache._evict_expired()
        assert await cache.get("key") is None


class TestTTLCache:
    @pytest.mark.asyncio
    async def test_get_or_set(self):
        backend = MemoryCache()
        cache = TTLCache(backend, default_ttl=300)

        async def factory():
            return "computed"

        result = await cache.get_or_set("key", factory)
        assert result == "computed"

        cached = await cache.get_or_set("key", factory)
        assert cached == "computed"


class TestCacheInvalidator:
    @pytest.mark.asyncio
    async def test_invalidate_group(self):
        backend = MemoryCache()
        invalidator = CacheInvalidator(backend)
        await backend.set("user:1", "data")
        await backend.set("user:2", "data")
        invalidator.register_pattern("users", "user:*")
        count = await invalidator.invalidate_group("users")
        assert count == 2

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self):
        backend = MemoryCache()
        invalidator = CacheInvalidator(backend)
        await backend.set("user:1", "data")
        count = await invalidator.invalidate_pattern("other:*")
        assert count == 0


class TestCacheNamespace:
    @pytest.mark.asyncio
    async def test_namespaced_get_set(self):
        backend = MemoryCache()
        ns = CacheNamespace(backend, "users")
        await ns.set("1", "alice")
        assert await ns.get("1") == "alice"
        assert await backend.get("users:1") == "alice"

    @pytest.mark.asyncio
    async def test_clear_namespace(self):
        backend = MemoryCache()
        ns = CacheNamespace(backend, "users")
        await ns.set("1", "alice")
        await ns.set("2", "bob")
        await ns.clear_namespace()
        assert await ns.get("1") is None


class TestNamespaceManager:
    @pytest.mark.asyncio
    async def test_get_namespace(self):
        backend = MemoryCache()
        mgr = NamespaceManager(backend)
        ns = mgr.get_namespace("users")
        assert isinstance(ns, CacheNamespace)
        assert mgr.get_namespace("users") is ns

    @pytest.mark.asyncio
    async def test_clear_all(self):
        backend = MemoryCache()
        mgr = NamespaceManager(backend)
        ns = mgr.get_namespace("users")
        await ns.set("1", "alice")
        await mgr.clear_all()
        assert await ns.get("1") is None
