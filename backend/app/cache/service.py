from __future__ import annotations

import json
from typing import Any, Callable

from app.core.config import get_settings
from app.core.logging import get_logger
from app.redis.client import RedisClient

logger = get_logger("cache.service")


class CacheService:
    """High-level cache service wrapping Redis with JSON serialization and stats."""

    def __init__(self, redis: RedisClient, default_ttl: int | None = None):
        self._redis = redis
        self._default_ttl = default_ttl or get_settings().default_cache_ttl
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Any:
        """Get a cached value, deserialized from JSON."""
        raw = await self._redis.get(key)
        if raw is None:
            self._misses += 1
            return None
        self._hits += 1
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set a cached value, serialized to JSON."""
        ttl = ttl if ttl is not None else self._default_ttl
        try:
            serialized = json.dumps(value, default=str)
            return await self._redis.set(key, serialized, ex=ttl)
        except (TypeError, ValueError) as exc:
            logger.error("Cache SET serialization failed for %s: %s", key, exc)
            return False

    async def delete(self, key: str) -> bool:
        """Delete a cached value."""
        return await self._redis.delete(key)

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a glob pattern."""
        keys = await self._redis._redis.keys(pattern)
        if not keys:
            return 0
        deleted = 0
        for key in keys:
            if await self._redis.delete(key):
                deleted += 1
        return deleted

    async def get_or_set(
        self, key: str, factory: Callable[[], Any], ttl: int | None = None
    ) -> Any:
        """Get from cache or compute via factory and cache the result."""
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = await factory() if self._is_async(factory) else factory()
        await self.set(key, value, ttl=ttl)
        return value

    async def get_stats(self) -> dict[str, int]:
        """Return cache hit/miss statistics."""
        total = self._hits + self._misses
        ratio = self._hits / total if total > 0 else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": round(ratio, 4),
        }

    def reset_stats(self) -> None:
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _is_async(fn: Callable) -> bool:
        import asyncio

        return asyncio.iscoroutinefunction(fn)
