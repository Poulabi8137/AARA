from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.approval.human import HumanApprovalManager
from app.approval.models import ApprovalCheckpoint, ApprovalDecision, CheckpointStatus
from app.workflow.checkpoint import CheckpointManager


class TestApprovalModels:
    def test_checkpoint_status_values(self) -> None:
        assert CheckpointStatus.PENDING == "pending"
        assert CheckpointStatus.APPROVED == "approved"
        assert CheckpointStatus.REJECTED == "rejected"
        assert CheckpointStatus.EXPIRED == "expired"
        assert CheckpointStatus.REVISION_REQUESTED == "revision_requested"

    def test_approval_decision_values(self) -> None:
        assert ApprovalDecision.APPROVE == "approve"
        assert ApprovalDecision.REJECT == "reject"
        assert ApprovalDecision.REVISE == "revise"
        assert ApprovalDecision.CONTINUE == "continue"

    def test_approval_checkpoint_defaults(self) -> None:
        cp = ApprovalCheckpoint(id="cp_1", workflow_id="wf_1", phase="review")
        assert cp.status == CheckpointStatus.PENDING
        assert cp.input_summary == ""
        assert cp.output_snapshot == {}
        assert cp.created_at is None
        assert cp.expires_at is None
        assert cp.decided_at is None
        assert cp.decision is None
        assert cp.notes == ""

    def test_approval_checkpoint_full(self) -> None:
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        cp = ApprovalCheckpoint(
            id="cp_1",
            workflow_id="wf_1",
            phase="review",
            status=CheckpointStatus.APPROVED,
            input_summary="test summary",
            output_snapshot={"key": "val"},
            created_at=now,
            expires_at=now,
            decided_at=now,
            decision="approve",
            notes="looks good",
        )
        assert cp.status == CheckpointStatus.APPROVED
        assert cp.input_summary == "test summary"
        assert cp.decision == "approve"


class TestHumanApprovalManager:
    @pytest.fixture
    def mock_cp_manager(self) -> MagicMock:
        mgr = MagicMock(spec=CheckpointManager)
        mgr.create_checkpoint = AsyncMock(return_value={
            "id": "cp_mock",
            "workflow_id": "wf_1",
            "phase": "review",
            "status": "pending",
            "output": {},
            "created_at": "2025-01-01T00:00:00+00:00",
            "expires_at": "2025-01-04T00:00:00+00:00",
            "decided_at": None,
            "decision": None,
            "notes": "",
        })
        mgr.get_checkpoint = AsyncMock(return_value={
            "id": "cp_mock",
            "workflow_id": "wf_1",
            "phase": "review",
            "status": "approved",
            "output": {},
            "created_at": "2025-01-01T00:00:00+00:00",
            "expires_at": "2025-01-04T00:00:00+00:00",
            "decided_at": "2025-01-02T00:00:00+00:00",
            "decision": "approved",
            "notes": "looks good",
        })
        mgr.list_checkpoints = AsyncMock(return_value=[
            {
                "id": "cp_pending",
                "workflow_id": "wf_1",
                "phase": "review",
                "status": "pending",
                "output": {},
                "created_at": "2025-01-01T00:00:00+00:00",
                "expires_at": "2025-01-04T00:00:00+00:00",
            },
            {
                "id": "cp_approved",
                "workflow_id": "wf_1",
                "phase": "review",
                "status": "approved",
                "output": {},
                "created_at": "2025-01-01T00:00:00+00:00",
                "expires_at": "2025-01-04T00:00:00+00:00",
            },
        ])
        mgr.resolve_checkpoint = AsyncMock(return_value=True)
        return mgr

    @pytest.fixture
    def manager(self, mock_cp_manager: MagicMock) -> HumanApprovalManager:
        return HumanApprovalManager(checkpoint_manager=mock_cp_manager)

    @pytest.mark.asyncio
    async def test_create_checkpoint(self, manager: HumanApprovalManager) -> None:
        cp = await manager.create_checkpoint(
            workflow_id="wf_1",
            phase="review",
            output_summary="summary text",
            output_snapshot={"key": "val"},
        )
        assert isinstance(cp, ApprovalCheckpoint)
        assert cp.workflow_id == "wf_1"
        assert cp.phase == "review"
        assert cp.status == CheckpointStatus.PENDING
        assert cp.input_summary == "summary text"
        assert cp.output_snapshot == {"key": "val"}
        assert cp.id.startswith("cp_")
        manager._checkpoint_manager.create_checkpoint.assert_awaited_once_with(
            workflow_id="wf_1", phase="review", output={"key": "val"}, ttl_hours=72
        )

    @pytest.mark.asyncio
    async def test_get_pending_checkpoints(self, manager: HumanApprovalManager) -> None:
        pending = await manager.get_pending_checkpoints("wf_1")
        assert len(pending) == 1
        assert pending[0].id == "cp_pending"
        assert pending[0].status == CheckpointStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_pending_checkpoints_none(
        self, mock_cp_manager: MagicMock
    ) -> None:
        mock_cp_manager.list_checkpoints = AsyncMock(return_value=[])
        manager = HumanApprovalManager(checkpoint_manager=mock_cp_manager)
        pending = await manager.get_pending_checkpoints("wf_empty")
        assert pending == []

    @pytest.mark.asyncio
    async def test_approve_updates_status(self, manager: HumanApprovalManager) -> None:
        ok = await manager.approve("cp_mock", notes="approved by reviewer")
        assert ok is True
        manager._checkpoint_manager.resolve_checkpoint.assert_awaited_once_with(
            "cp_mock", "approved", notes="approved by reviewer"
        )

    @pytest.mark.asyncio
    async def test_approve_resumes_workflow(self, manager: HumanApprovalManager) -> None:
        ok = await manager.approve("cp_mock")
        assert ok is True

    @pytest.mark.asyncio
    async def test_approve_failure_returns_false(self, mock_cp_manager: MagicMock) -> None:
        mock_cp_manager.resolve_checkpoint = AsyncMock(return_value=False)
        manager = HumanApprovalManager(checkpoint_manager=mock_cp_manager)
        ok = await manager.approve("nonexistent")
        assert ok is False

    @pytest.mark.asyncio
    async def test_reject_updates_status(self, manager: HumanApprovalManager) -> None:
        ok = await manager.reject("cp_mock", reason="does not meet criteria", action="modify_query")
        assert ok is True
        manager._checkpoint_manager.resolve_checkpoint.assert_awaited_once_with(
            "cp_mock", "rejected", notes="does not meet criteria (action: modify_query)"
        )

    @pytest.mark.asyncio
    async def test_request_revision_updates_status(self, manager: HumanApprovalManager) -> None:
        ok = await manager.request_revision("cp_mock", instructions="please update section 3")
        assert ok is True
        manager._checkpoint_manager.resolve_checkpoint.assert_awaited_once_with(
            "cp_mock", "revision_requested", notes="please update section 3"
        )

    @pytest.mark.asyncio
    async def test_continue_workflow(self, manager: HumanApprovalManager) -> None:
        ok = await manager.continue_workflow("cp_mock")
        assert ok is True
        manager._checkpoint_manager.resolve_checkpoint.assert_awaited_once_with(
            "cp_mock", "continued"
        )

    @pytest.mark.asyncio
    async def test_get_checkpoint(self, manager: HumanApprovalManager) -> None:
        cp = await manager.get_checkpoint("cp_mock")
        assert cp is not None
        assert isinstance(cp, ApprovalCheckpoint)
        assert cp.id == "cp_mock"
        assert cp.status == CheckpointStatus.APPROVED
        assert cp.decision == "approved"
        assert cp.notes == "looks good"

    @pytest.mark.asyncio
    async def test_get_checkpoint_not_found(self, mock_cp_manager: MagicMock) -> None:
        mock_cp_manager.get_checkpoint = AsyncMock(return_value=None)
        manager = HumanApprovalManager(checkpoint_manager=mock_cp_manager)
        cp = await manager.get_checkpoint("nonexistent")
        assert cp is None

    @pytest.mark.asyncio
    async def test_pause_workflow(self, manager: HumanApprovalManager) -> None:
        ok = await manager.pause_workflow("wf_1")
        assert ok is True
        assert manager._paused_workflows["wf_1"] is True

    @pytest.mark.asyncio
    async def test_resume_workflow(self, manager: HumanApprovalManager) -> None:
        await manager.pause_workflow("wf_1")
        ok = await manager.resume_workflow("wf_1")
        assert ok is True
        assert manager._paused_workflows["wf_1"] is False

    @pytest.mark.asyncio
    async def test_pause_resume_state_transition(self, manager: HumanApprovalManager) -> None:
        await manager.pause_workflow("wf_1")
        assert manager._paused_workflows["wf_1"] is True
        await manager.resume_workflow("wf_1")
        assert manager._paused_workflows["wf_1"] is False

    @pytest.mark.asyncio
    async def test_approve_fetches_checkpoint_data(
        self, mock_cp_manager: MagicMock
    ) -> None:
        get_checkpoint_mock = AsyncMock(return_value={
            "id": "cp_mock",
            "workflow_id": "wf_1",
            "phase": "review",
            "status": "approved",
            "output": {},
            "created_at": "2025-01-01T00:00:00+00:00",
            "expires_at": "2025-01-04T00:00:00+00:00",
            "decided_at": "2025-01-02T00:00:00+00:00",
            "decision": "approved",
            "notes": "",
        })
        mock_cp_manager.get_checkpoint = get_checkpoint_mock
        mock_cp_manager.resolve_checkpoint = AsyncMock(return_value=True)
        manager = HumanApprovalManager(checkpoint_manager=mock_cp_manager)
        ok = await manager.approve("cp_mock")
        assert ok is True

    @pytest.mark.asyncio
    async def test_continue_fetches_checkpoint_data(
        self, mock_cp_manager: MagicMock
    ) -> None:
        get_checkpoint_mock = AsyncMock(return_value={
            "id": "cp_mock",
            "workflow_id": "wf_2",
            "phase": "review",
            "status": "continued",
            "output": {},
            "created_at": "2025-01-01T00:00:00+00:00",
            "expires_at": "2025-01-04T00:00:00+00:00",
            "decided_at": "2025-01-02T00:00:00+00:00",
            "decision": "continued",
            "notes": "",
        })
        mock_cp_manager.get_checkpoint = get_checkpoint_mock
        mock_cp_manager.resolve_checkpoint = AsyncMock(return_value=True)
        manager = HumanApprovalManager(checkpoint_manager=mock_cp_manager)
        ok = await manager.continue_workflow("cp_mock")
        assert ok is True

    @pytest.mark.asyncio
    async def test_approve_does_not_break_if_get_checkpoint_returns_none(
        self, mock_cp_manager: MagicMock
    ) -> None:
        mock_cp_manager.resolve_checkpoint = AsyncMock(return_value=True)
        mock_cp_manager.get_checkpoint = AsyncMock(return_value=None)
        manager = HumanApprovalManager(checkpoint_manager=mock_cp_manager)
        ok = await manager.approve("cp_mock")
        assert ok is True
