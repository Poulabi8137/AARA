from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.approval.models import ApprovalCheckpoint, CheckpointStatus
from app.workflow.checkpoint import CheckpointManager


class HumanApprovalManager:
    def __init__(self, checkpoint_manager: CheckpointManager | None = None) -> None:
        self._checkpoint_manager = checkpoint_manager or CheckpointManager()
        self._paused_workflows: dict[str, bool] = {}

    async def create_checkpoint(
        self,
        workflow_id: str,
        phase: str,
        output_summary: str,
        output_snapshot: dict[str, Any],
        ttl_hours: int = 72,
    ) -> ApprovalCheckpoint:
        now = datetime.now(UTC)
        cp = ApprovalCheckpoint(
            id=f"cp_{uuid4().hex[:12]}",
            workflow_id=workflow_id,
            phase=phase,
            status=CheckpointStatus.PENDING,
            input_summary=output_summary,
            output_snapshot=output_snapshot,
            created_at=now,
            expires_at=now.replace(hour=(now.hour + ttl_hours) % 24),
        )
        await self._checkpoint_manager.create_checkpoint(
            workflow_id=workflow_id,
            phase=phase,
            output=output_snapshot,
            ttl_hours=ttl_hours,
        )
        return cp

    async def get_pending_checkpoints(self, workflow_id: str) -> list[ApprovalCheckpoint]:
        raw_list = await self._checkpoint_manager.list_checkpoints(workflow_id)
        result: list[ApprovalCheckpoint] = []
        for raw in raw_list:
            if raw.get("status") == "pending":
                result.append(ApprovalCheckpoint(
                    id=raw["id"],
                    workflow_id=raw["workflow_id"],
                    phase=raw["phase"],
                    status=CheckpointStatus.PENDING,
                    input_summary="",
                    output_snapshot={},
                    created_at=datetime.fromisoformat(raw["created_at"]),
                    expires_at=datetime.fromisoformat(raw["expires_at"]),
                ))
        return result

    async def approve(self, checkpoint_id: str, notes: str = "") -> bool:
        ok = await self._checkpoint_manager.resolve_checkpoint(
            checkpoint_id, "approved", notes=notes,
        )
        if ok:
            cp_data = await self._checkpoint_manager.get_checkpoint(checkpoint_id)
            if cp_data:
                await self.resume_workflow(cp_data["workflow_id"])
        return ok

    async def reject(self, checkpoint_id: str, reason: str, action: str = "modify_query") -> bool:
        return await self._checkpoint_manager.resolve_checkpoint(
            checkpoint_id, "rejected", notes=f"{reason} (action: {action})",
        )

    async def request_revision(self, checkpoint_id: str, instructions: str) -> bool:
        return await self._checkpoint_manager.resolve_checkpoint(
            checkpoint_id, "revision_requested", notes=instructions,
        )

    async def continue_workflow(self, checkpoint_id: str) -> bool:
        ok = await self._checkpoint_manager.resolve_checkpoint(
            checkpoint_id, "continued",
        )
        if ok:
            cp_data = await self._checkpoint_manager.get_checkpoint(checkpoint_id)
            if cp_data:
                await self.resume_workflow(cp_data["workflow_id"])
        return ok

    async def get_checkpoint(self, checkpoint_id: str) -> ApprovalCheckpoint | None:
        raw = await self._checkpoint_manager.get_checkpoint(checkpoint_id)
        if raw is None:
            return None
        return ApprovalCheckpoint(
            id=raw["id"],
            workflow_id=raw["workflow_id"],
            phase=raw["phase"],
            status=CheckpointStatus(raw.get("status", "pending")),
            input_summary="",
            output_snapshot=raw.get("output", {}),
            created_at=datetime.fromisoformat(raw["created_at"]),
            expires_at=datetime.fromisoformat(raw["expires_at"]),
            decided_at=datetime.fromisoformat(raw["decided_at"]) if raw.get("decided_at") else None,
            decision=raw.get("decision"),
            notes=raw.get("notes", ""),
        )

    async def pause_workflow(self, workflow_id: str) -> bool:
        self._paused_workflows[workflow_id] = True
        return True

    async def resume_workflow(self, workflow_id: str) -> bool:
        self._paused_workflows[workflow_id] = False
        return True
