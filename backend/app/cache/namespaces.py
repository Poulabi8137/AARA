from __future__ import annotations

from typing import Any

from app.cache.interface import CacheBackend


class CacheNamespace:
    def __init__(self, backend: CacheBackend, namespace: str, separator: str = ":") -> None:
        self._backend = backend
        self._namespace = namespace
        self._separator = separator

    def _key(self, key: str) -> str:
        return f"{self._namespace}{self._separator}{key}"

    async def get(self, key: str) -> Any:
        return await self._backend.get(self._key(key))

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        await self._backend.set(self._key(key), value, ttl)

    async def delete(self, key: str) -> bool:
        return await self._backend.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        return await self._backend.exists(self._key(key))

    async def clear_namespace(self) -> None:
        if hasattr(self._backend, "_store"):
            prefix = f"{self._namespace}{self._separator}"
            keys_to_delete = [
                k for k in self._backend._store
                if k.startswith(prefix)
            ]
            for key in keys_to_delete:
                await self._backend.delete(key)


class NamespaceManager:
    def __init__(self, backend: CacheBackend) -> None:
        self._backend = backend
        self._namespaces: dict[str, CacheNamespace] = {}

    def get_namespace(self, name: str, separator: str = ":") -> CacheNamespace:
        if name not in self._namespaces:
            self._namespaces[name] = CacheNamespace(self._backend, name, separator)
        return self._namespaces[name]

    async def clear_all(self) -> None:
        for ns in self._namespaces.values():
            await ns.clear_namespace()
