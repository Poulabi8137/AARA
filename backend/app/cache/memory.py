from __future__ import annotations

import time
from typing import Any

from app.cache.interface import CacheBackend


class MemoryCache(CacheBackend):
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._expiry: dict[str, float] = {}

    async def get(self, key: str) -> Any:
        self._evict_expired()
        return self._store.get(key)

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        self._store[key] = value
        if ttl is not None and ttl > 0:
            self._expiry[key] = time.time() + ttl

    async def delete(self, key: str) -> bool:
        existed = key in self._store
        self._store.pop(key, None)
        self._expiry.pop(key, None)
        return existed

    async def exists(self, key: str) -> bool:
        self._evict_expired()
        return key in self._store

    async def clear(self) -> None:
        self._store.clear()
        self._expiry.clear()

    async def size(self) -> int:
        self._evict_expired()
        return len(self._store)

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [k for k, t in self._expiry.items() if t <= now]
        for k in expired:
            self._store.pop(k, None)
            self._expiry.pop(k, None)
