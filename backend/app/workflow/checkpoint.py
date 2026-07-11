from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    pass


class CheckpointManager:
    def __init__(self) -> None:
        self._checkpoints: dict[str, dict[str, Any]] = {}

    async def create_checkpoint(
        self,
        workflow_id: str,
        phase: str,
        output: Any,
        ttl_hours: int = 72,
    ) -> dict[str, Any]:
        checkpoint_id = f"cp_{uuid4().hex[:12]}"
        now = datetime.now(UTC)
        checkpoint = {
            "id": checkpoint_id,
            "workflow_id": workflow_id,
            "phase": phase,
            "status": "pending",
            "output": output,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=ttl_hours)).isoformat(),
            "decided_at": None,
            "decision": None,
            "notes": "",
        }
        self._checkpoints[checkpoint_id] = checkpoint
        return checkpoint

    async def get_checkpoint(self, checkpoint_id: str) -> dict[str, Any] | None:
        return self._checkpoints.get(checkpoint_id)

    async def list_checkpoints(self, workflow_id: str) -> list[dict[str, Any]]:
        return [
            cp for cp in self._checkpoints.values()
            if cp["workflow_id"] == workflow_id
        ]

    async def resolve_checkpoint(self, checkpoint_id: str, decision: str, notes: str = "") -> bool:
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            return False
        checkpoint["status"] = decision
        checkpoint["decided_at"] = datetime.now(UTC).isoformat()
        checkpoint["decision"] = decision
        checkpoint["notes"] = notes
        return True

    async def expire_stale_checkpoints(self) -> int:
        now = datetime.now(UTC)
        expired = 0
        for _cp_id, cp in list(self._checkpoints.items()):
            if cp["status"] != "pending":
                continue
            expires_at = datetime.fromisoformat(cp["expires_at"])
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if now >= expires_at:
                cp["status"] = "expired"
                expired += 1
        return expired
