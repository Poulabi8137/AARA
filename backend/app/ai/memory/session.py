from __future__ import annotations

import asyncio
from typing import Any


class SessionMemory:
    def __init__(self, session_id: str, max_size_bytes: int = 10 * 1024 * 1024) -> None:
        self.session_id = session_id
        self._store: dict[str, Any] = {}
        self._context_stack: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._max_size = max_size_bytes

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._store[key] = value

    async def get(self, key: str) -> Any | None:
        return self._store.get(key)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            return self._store.pop(key, None) is not None

    async def push_context(self, entry: dict[str, Any]) -> None:
        async with self._lock:
            self._context_stack.append(entry)

    async def get_context(self) -> list[dict[str, Any]]:
        return self._context_stack.copy()

    async def pop_context(self) -> dict[str, Any] | None:
        async with self._lock:
            if self._context_stack:
                return self._context_stack.pop()
            return None

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()
            self._context_stack.clear()

    async def snapshot(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "store": self._store.copy(),
            "context_stack": self._context_stack.copy(),
        }

    async def restore(self, snapshot: dict[str, Any]) -> None:
        self._store = snapshot.get("store", {}).copy()
        self._context_stack = snapshot.get("context_stack", []).copy()

    async def size(self) -> int:
        async with self._lock:
            import json
            return len(json.dumps({"s": self._store, "c": self._context_stack}))

    async def keys(self) -> list[str]:
        return list(self._store.keys())
