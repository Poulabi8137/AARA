from __future__ import annotations

from enum import Enum
from typing import Any


class MemoryEvictionPolicy(Enum):
    LRU = "lru"
    FIFO = "fifo"
    TTL = "ttl"


class MemoryEvictionStrategy:
    def __init__(
        self, policy: MemoryEvictionPolicy = MemoryEvictionPolicy.LRU, max_entries: int = 1000
    ) -> None:
        self.policy = policy
        self.max_entries = max_entries
        self._access_order: list[str] = []

    def should_evict(self, current_size: int) -> bool:
        return current_size > self.max_entries

    def record_access(self, key: str) -> None:
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    def get_eviction_candidates(self, current_store: dict[str, Any]) -> list[str]:
        excess = len(current_store) - self.max_entries
        if excess <= 0:
            return []

        if self.policy == MemoryEvictionPolicy.FIFO:
            return list(current_store.keys())[:excess]
        elif self.policy == MemoryEvictionPolicy.LRU:
            oldest = self._access_order[:excess]
            return [k for k in oldest if k in current_store]
        return []

    async def evict(self, store: dict[str, Any], memory_type: str = "session") -> int:
        candidates = self.get_eviction_candidates(store)
        for key in candidates:
            store.pop(key, None)
        return len(candidates)
