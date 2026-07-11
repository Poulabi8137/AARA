from __future__ import annotations

import re

from app.cache.interface import CacheBackend


class CacheInvalidator:
    def __init__(self, backend: CacheBackend) -> None:
        self._backend = backend
        self._key_patterns: dict[str, list[str]] = {}

    def register_pattern(self, group: str, pattern: str) -> None:
        if group not in self._key_patterns:
            self._key_patterns[group] = []
        self._key_patterns[group].append(pattern)

    async def invalidate_group(self, group: str) -> int:
        count = 0
        for pattern in self._key_patterns.get(group, []):
            keys = await self._find_keys(pattern)
            for key in keys:
                if await self._backend.delete(key):
                    count += 1
        return count

    async def invalidate_pattern(self, pattern: str) -> int:
        keys = await self._find_keys(pattern)
        count = 0
        for key in keys:
            if await self._backend.delete(key):
                count += 1
        return count

    async def _find_keys(self, pattern: str) -> list[str]:
        regex = re.compile(pattern.replace("*", ".*").replace("?", "."))
        if hasattr(self._backend, "_store"):
            return [k for k in self._backend._store if regex.match(k)]
        return []
