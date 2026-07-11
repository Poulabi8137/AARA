from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4


class IdempotencyManager:
    TTL = timedelta(hours=24)

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, datetime]] = {}

    def _make_key(self, key: str, user_id: str, workspace_id: str, query: str) -> str:
        raw = f"{key}:{user_id}:{workspace_id}:{query}"
        return sha256(raw.encode("utf-8")).hexdigest()

    async def get_or_create(
        self,
        key: str,
        user_id: str,
        workspace_id: str,
        query: str,
    ) -> tuple[str, bool]:
        store_key = self._make_key(key, user_id, workspace_id, query)
        now = datetime.now(UTC)
        existing = self._store.get(store_key)
        if existing:
            wf_id, created = existing
            if now - created < self.TTL:
                return wf_id, False
        workflow_id = f"wf_{uuid4().hex[:12]}"
        self._store[store_key] = (workflow_id, now)
        self._evict_expired()
        return workflow_id, True

    async def is_processed(self, key: str, user_id: str = "", workspace_id: str = "", query: str = "") -> bool:  # noqa: E501
        self._evict_expired()
        store_key = self._make_key(key, user_id, workspace_id, query)
        return store_key in self._store

    def _evict_expired(self) -> None:
        now = datetime.now(UTC)
        for store_key, (_wf_id, created) in list(self._store.items()):
            if now - created >= self.TTL:
                del self._store[store_key]
