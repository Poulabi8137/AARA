from __future__ import annotations

from typing import Any

from app.cache.interface import CacheBackend


class TTLCache:
    def __init__(self, backend: CacheBackend, default_ttl: float = 300.0) -> None:
        self._backend = backend
        self._default_ttl = default_ttl

    async def get(self, key: str) -> Any:
        return await self._backend.get(key)

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        await self._backend.set(key, value, ttl or self._default_ttl)

    async def get_or_set(
        self, key: str, factory: Any, ttl: float | None = None,
    ) -> Any:
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = await factory()
        await self.set(key, value, ttl)
        return value

    async def delete(self, key: str) -> bool:
        return await self._backend.delete(key)

    async def exists(self, key: str) -> bool:
        return await self._backend.exists(key)

    async def clear(self) -> None:
        await self._backend.clear()
