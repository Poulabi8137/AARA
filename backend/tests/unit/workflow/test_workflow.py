from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.models import AgentStep
from app.agents.task_graph import TaskGraph
from app.plugins.agent_registry import AgentRegistry
from app.workflow.checkpoint import CheckpointManager
from app.workflow.engine import WorkflowEngine
from app.workflow.idempotency import IdempotencyManager
from app.workflow.types import (
    ExecutionType,
    WorkflowDefinition,
    WorkflowState,
    WorkflowStatus,
    WorkflowStepResult,
)


class TestWorkflowTypes:
    def test_execution_type_values(self) -> None:
        assert ExecutionType.SEQUENTIAL == "sequential"
        assert ExecutionType.PARALLEL == "parallel"
        assert ExecutionType.DEPENDENCY == "dependency"

    def test_workflow_definition_defaults(self) -> None:
        wd = WorkflowDefinition(workflow_type="test")
        assert wd.workflow_type == "test"
        assert wd.description == ""
        assert wd.agents == []
        assert wd.handler is None
        assert wd.execution_type == ExecutionType.SEQUENTIAL
        assert wd.timeout_seconds == 300
        assert wd.max_retries == 3
        assert wd.checkpoint_phases == []

    def test_workflow_definition_custom(self) -> None:
        wd = WorkflowDefinition(
            workflow_type="custom",
            description="custom workflow",
            agents=["a1", "a2"],
            execution_type=ExecutionType.PARALLEL,
            timeout_seconds=600,
            max_retries=5,
            checkpoint_phases=["phase1"],
        )
        assert wd.workflow_type == "custom"
        assert wd.description == "custom workflow"
        assert wd.agents == ["a1", "a2"]
        assert wd.execution_type == ExecutionType.PARALLEL
        assert wd.timeout_seconds == 600
        assert wd.max_retries == 5
        assert wd.checkpoint_phases == ["phase1"]

    def test_workflow_step_result_defaults(self) -> None:
        result = WorkflowStepResult(step_id="s1", agent_id="a1", status="pending")
        assert result.step_id == "s1"
        assert result.agent_id == "a1"
        assert result.status == "pending"
        assert result.output is None
        assert result.error is None
        assert result.duration_ms == 0
        assert result.started_at is None
        assert result.completed_at is None

    def test_workflow_step_result_full(self) -> None:
        now = datetime.now(UTC)
        result = WorkflowStepResult(
            step_id="s1",
            agent_id="a1",
            status="completed",
            output={"key": "val"},
            error=None,
            duration_ms=150,
            started_at=now,
            completed_at=now,
        )
        assert result.output == {"key": "val"}
        assert result.duration_ms == 150

    def test_workflow_state_defaults(self) -> None:
        state = WorkflowState(workflow_id="wf_abc")
        assert state.status == WorkflowStatus.PENDING
        assert state.current_step == ""
        assert state.completed_steps == []
        assert state.failed_steps == []
        assert state.step_results == {}
        assert state.start_time is None
        assert state.end_time is None
        assert state.error is None
        assert state.checkpoint_data == {}

    def test_workflow_state_custom(self) -> None:
        now = datetime.now(UTC)
        state = WorkflowState(
            workflow_id="wf_custom",
            status=WorkflowStatus.RUNNING,
            current_step="step2",
            completed_steps=["step1"],
            failed_steps=[],
            step_results={},
            start_time=now,
            end_time=None,
            error=None,
            checkpoint_data={"key": "val"},
        )
        assert state.status == WorkflowStatus.RUNNING
        assert state.current_step == "step2"
        assert state.checkpoint_data == {"key": "val"}


class TestCheckpointManager:
    @pytest.fixture
    def manager(self) -> CheckpointManager:
        return CheckpointManager()

    @pytest.mark.asyncio
    async def test_create_checkpoint(self, manager: CheckpointManager) -> None:
        cp = await manager.create_checkpoint("wf_1", "phase1", {"result": "ok"})
        assert cp["workflow_id"] == "wf_1"
        assert cp["phase"] == "phase1"
        assert cp["output"] == {"result": "ok"}
        assert cp["status"] == "pending"
        assert cp["id"].startswith("cp_")
        assert cp["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_get_checkpoint_found(self, manager: CheckpointManager) -> None:
        created = await manager.create_checkpoint("wf_1", "phase1", {})
        retrieved = await manager.get_checkpoint(created["id"])
        assert retrieved is not None
        assert retrieved["id"] == created["id"]

    @pytest.mark.asyncio
    async def test_get_checkpoint_not_found(self, manager: CheckpointManager) -> None:
        assert await manager.get_checkpoint("nonexistent") is None

    @pytest.mark.asyncio
    async def test_list_checkpoints(self, manager: CheckpointManager) -> None:
        await manager.create_checkpoint("wf_1", "p1", {})
        await manager.create_checkpoint("wf_1", "p2", {})
        await manager.create_checkpoint("wf_2", "p1", {})
        result = await manager.list_checkpoints("wf_1")
        assert len(result) == 2
        assert all(cp["workflow_id"] == "wf_1" for cp in result)

    @pytest.mark.asyncio
    async def test_resolve_checkpoint(self, manager: CheckpointManager) -> None:
        cp = await manager.create_checkpoint("wf_1", "phase1", {})
        ok = await manager.resolve_checkpoint(cp["id"], "approved", notes="looks good")
        assert ok is True
        resolved = await manager.get_checkpoint(cp["id"])
        assert resolved is not None
        assert resolved["status"] == "approved"
        assert resolved["decision"] == "approved"
        assert resolved["notes"] == "looks good"
        assert resolved["decided_at"] is not None

    @pytest.mark.asyncio
    async def test_resolve_checkpoint_not_found(self, manager: CheckpointManager) -> None:
        ok = await manager.resolve_checkpoint("nonexistent", "approved")
        assert ok is False

    @pytest.mark.asyncio
    async def test_expire_stale_checkpoints(self, manager: CheckpointManager) -> None:
        await manager.create_checkpoint("wf_1", "p1", {}, ttl_hours=0)
        expired_count = await manager.expire_stale_checkpoints()
        assert expired_count == 1

    @pytest.mark.asyncio
    async def test_expire_stale_skips_resolved(self, manager: CheckpointManager) -> None:
        cp = await manager.create_checkpoint("wf_1", "p1", {}, ttl_hours=0)
        await manager.resolve_checkpoint(cp["id"], "approved")
        expired_count = await manager.expire_stale_checkpoints()
        assert expired_count == 0

    @pytest.mark.asyncio
    async def test_duplicate_checkpoint_does_not_raise(self, manager: CheckpointManager) -> None:
        cp1 = await manager.create_checkpoint("wf_1", "p1", {})
        cp2 = await manager.create_checkpoint("wf_1", "p1", {})
        assert cp1["id"] != cp2["id"]
        assert cp1["workflow_id"] == cp2["workflow_id"]


class TestIdempotencyManager:
    @pytest.fixture
    def manager(self) -> IdempotencyManager:
        return IdempotencyManager()

    @pytest.mark.asyncio
    async def test_make_key_deterministic(self, manager: IdempotencyManager) -> None:
        key1 = manager._make_key("k", "u", "w", "q")
        key2 = manager._make_key("k", "u", "w", "q")
        assert key1 == key2

    @pytest.mark.asyncio
    async def test_make_key_different_inputs(self, manager: IdempotencyManager) -> None:
        key1 = manager._make_key("k", "u1", "w", "q")
        key2 = manager._make_key("k", "u2", "w", "q")
        assert key1 != key2

    @pytest.mark.asyncio
    async def test_get_or_create_new(self, manager: IdempotencyManager) -> None:
        wf_id, is_new = await manager.get_or_create("key", "user1", "ws1", "query1")
        assert is_new is True
        assert wf_id.startswith("wf_")

    @pytest.mark.asyncio
    async def test_get_or_create_duplicate(self, manager: IdempotencyManager) -> None:
        wf_id1, is_new1 = await manager.get_or_create("key", "user1", "ws1", "query1")
        assert is_new1 is True
        wf_id2, is_new2 = await manager.get_or_create("key", "user1", "ws1", "query1")
        assert is_new2 is False
        assert wf_id2 == wf_id1

    @pytest.mark.asyncio
    async def test_get_or_create_different_query_not_duplicate(
        self, manager: IdempotencyManager
    ) -> None:
        wf_id1, _ = await manager.get_or_create("key", "user1", "ws1", "query1")
        wf_id2, is_new = await manager.get_or_create("key", "user1", "ws1", "query2")
        assert is_new is True
        assert wf_id1 != wf_id2

    @pytest.mark.asyncio
    async def test_is_processed(self, manager: IdempotencyManager) -> None:
        await manager.get_or_create("session1", "u", "w", "q")
        assert await manager.is_processed("session1", "u", "w", "q") is True

    @pytest.mark.asyncio
    async def test_is_processed_not_found(self, manager: IdempotencyManager) -> None:
        assert await manager.is_processed("nonexistent", "u", "w", "q") is False

    @pytest.mark.asyncio
    async def test_ttl_expiry(self, manager: IdempotencyManager) -> None:
        original_ttl = IdempotencyManager.TTL
        try:
            IdempotencyManager.TTL = timedelta(hours=0)
            wf_id, is_new = await manager.get_or_create("key", "u", "w", "q")
            assert is_new is True
            wf_id2, is_new2 = await manager.get_or_create("key", "u", "w", "q")
            assert is_new2 is True
            assert wf_id != wf_id2
        finally:
            IdempotencyManager.TTL = original_ttl

    @pytest.mark.asyncio
    async def test_evict_expired(self, manager: IdempotencyManager) -> None:
        import uuid
        expired_time = datetime.now(UTC) - timedelta(hours=25)
        store_key = manager._make_key("key", "u", "w", "q")
        manager._store[store_key] = (f"wf_{uuid.uuid4().hex[:12]}", expired_time)
        assert len(manager._store) > 0
        manager._evict_expired()
        assert len(manager._store) == 0

    @pytest.mark.asyncio
    async def test_deduplication_in_fast_succession(self, manager: IdempotencyManager) -> None:
        results = []
        for _ in range(5):
            wf_id, is_new = await manager.get_or_create("key", "u", "w", "q")
            results.append((wf_id, is_new))
        assert all(r[1] is False for r in results[1:])
        assert all(r[0] == results[0][0] for r in results)


class TestWorkflowEngine:
    @pytest.fixture
    def mock_agent(self) -> MagicMock:
        agent = MagicMock()
        agent.agent_id = ""
        agent.execute = AsyncMock(return_value={"result": "success"})
        return agent

    @pytest.fixture
    def mock_agent_fail(self) -> MagicMock:
        agent = MagicMock()
        agent.agent_id = ""
        agent.execute = AsyncMock(side_effect=Exception("execution error"))
        return agent

    @pytest.fixture
    def mock_registry(self, mock_agent: MagicMock) -> MagicMock:
        registry = MagicMock(spec=AgentRegistry)
        registry.get.return_value = mock_agent
        return registry

    @pytest.fixture
    def mock_registry_fail(self, mock_agent_fail: MagicMock) -> MagicMock:
        registry = MagicMock(spec=AgentRegistry)
        registry.get.return_value = mock_agent_fail
        return registry

    @pytest.fixture
    def engine(self, mock_registry: MagicMock) -> WorkflowEngine:
        tg = TaskGraph()
        return WorkflowEngine(task_graph=tg, agent_registry=mock_registry)

    @pytest.fixture
    def engine_fail(self, mock_registry_fail: MagicMock) -> WorkflowEngine:
        tg = TaskGraph()
        return WorkflowEngine(task_graph=tg, agent_registry=mock_registry_fail)

    @pytest.fixture
    def workflow_def(self) -> WorkflowDefinition:
        return WorkflowDefinition(workflow_type="test", agents=["agent1", "agent2"])

    def make_step(self, agent_id: str, **kwargs: object) -> AgentStep:
        return AgentStep(agent_id=agent_id, **kwargs)

    @pytest.mark.asyncio
    async def test_create_workflow(self, engine: WorkflowEngine, workflow_def: WorkflowDefinition) -> None:
        wf_id = await engine.create_workflow(workflow_def, {"input": "data"})
        assert wf_id.startswith("wf_")
        assert engine.state is not None
        assert engine.state.status == WorkflowStatus.PENDING
        assert engine.state.workflow_id == wf_id
        assert engine.state.start_time is not None

    @pytest.mark.asyncio
    async def test_properties(self, engine: WorkflowEngine, workflow_def: WorkflowDefinition) -> None:
        assert engine.is_running is False
        assert engine.is_paused is False
        assert engine.is_cancelled is False
        await engine.create_workflow(workflow_def, {})
        assert engine._state is not None
        assert engine.state is engine._state

    @pytest.mark.asyncio
    async def test_execute_sequential_success(
        self, engine: WorkflowEngine, workflow_def: WorkflowDefinition
    ) -> None:
        await engine.create_workflow(workflow_def, {})
        steps = [self.make_step("agent1"), self.make_step("agent2")]
        results = await engine.execute_sequential(steps)
        assert len(results) == 2
        assert all(r.status == "completed" for r in results)
        assert engine.state is not None
        assert engine.state.completed_steps == ["agent1", "agent2"]

    @pytest.mark.asyncio
    async def test_execute_sequential_with_failure(
        self, engine_fail: WorkflowEngine, workflow_def: WorkflowDefinition
    ) -> None:
        await engine_fail.create_workflow(workflow_def, {})
        steps = [self.make_step("agent1"), self.make_step("agent2")]
        results = await engine_fail.execute_sequential(steps)
        assert all(r.status == "failed" for r in results)
        assert engine_fail.state is not None
        assert "agent1" in engine_fail.state.failed_steps

    @pytest.mark.asyncio
    async def test_execute_sequential_cancelled(
        self, engine: WorkflowEngine, workflow_def: WorkflowDefinition
    ) -> None:
        await engine.create_workflow(workflow_def, {})
        engine._cancelled = True
        steps = [self.make_step("agent1"), self.make_step("agent2")]
        results = await engine.execute_sequential(steps)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_execute_parallel_success(
        self, engine: WorkflowEngine, workflow_def: WorkflowDefinition
    ) -> None:
        await engine.create_workflow(workflow_def, {})
        steps = [self.make_step("agent1"), self.make_step("agent2"), self.make_step("agent3")]
        results = await engine.execute_parallel(steps)
        assert len(results) == 3
        assert all(r.status == "completed" for r in results)

    @pytest.mark.asyncio
    async def test_execute_parallel_with_failure(
        self, engine_fail: WorkflowEngine, workflow_def: WorkflowDefinition
    ) -> None:
        await engine_fail.create_workflow(workflow_def, {})
        steps = [self.make_step("agent1"), self.make_step("agent2")]
        results = await engine_fail.execute_parallel(steps)
        assert all(r.status == "failed" for r in results)

    @pytest.mark.asyncio
    async def test_execute_parallel_cancelled(
        self, engine: WorkflowEngine, workflow_def: WorkflowDefinition
    ) -> None:
        await engine.create_workflow(workflow_def, {})
        engine._cancelled = True
        steps = [self.make_step("agent1"), self.make_step("agent2")]
        results = await engine.execute_parallel(steps)
        assert all(r.status == "cancelled" for r in results)

    @pytest.mark.asyncio
    async def test_execute_dependency_topological_order(
        self, mock_registry: MagicMock, workflow_def: WorkflowDefinition
    ) -> None:
        tg = TaskGraph()
        step_a = self.make_step("A")
        step_b = self.make_step("B", depends_on=["A"])
        step_c = self.make_step("C", depends_on=["A"])
        step_d = self.make_step("D", depends_on=["B", "C"])
        tg.add_step(step_a)
        tg.add_step(step_b)
        tg.add_step(step_c)
        tg.add_step(step_d)

        engine = WorkflowEngine(task_graph=tg, agent_registry=mock_registry)
        await engine.create_workflow(workflow_def, {})
        results = await engine.execute_dependency(tg)
        assert len(results) == 4
        assert engine.state is not None
        assert len(engine.state.completed_steps) == 4
        assert "A" in engine.state.completed_steps
        assert "D" in engine.state.completed_steps

    @pytest.mark.asyncio
    async def test_execute_dependency_cancelled(
        self, mock_registry: MagicMock, workflow_def: WorkflowDefinition
    ) -> None:
        tg = TaskGraph()
        step_a = self.make_step("A")
        tg.add_step(step_a)
        engine = WorkflowEngine(task_graph=tg, agent_registry=mock_registry)
        await engine.create_workflow(workflow_def, {})
        engine._cancelled = True
        results = await engine.execute_dependency(tg)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_pause_workflow(self, engine: WorkflowEngine, workflow_def: WorkflowDefinition) -> None:
        await engine.create_workflow(workflow_def, {})
        engine._state.status = WorkflowStatus.RUNNING
        ok = await engine.pause()
        assert ok is True
        assert engine._state.status == WorkflowStatus.PAUSED
        assert engine._pause_event.is_set() is False

    @pytest.mark.asyncio
    async def test_pause_not_running(self, engine: WorkflowEngine, workflow_def: WorkflowDefinition) -> None:
        await engine.create_workflow(workflow_def, {})
        ok = await engine.pause()
        assert ok is False

    @pytest.mark.asyncio
    async def test_resume_workflow(self, engine: WorkflowEngine, workflow_def: WorkflowDefinition) -> None:
        await engine.create_workflow(workflow_def, {})
        engine._state.status = WorkflowStatus.PAUSED
        engine._pause_event.clear()
        ok = await engine.resume()
        assert ok is True
        assert engine._state.status == WorkflowStatus.RUNNING
        assert engine._pause_event.is_set() is True

    @pytest.mark.asyncio
    async def test_resume_not_paused(self, engine: WorkflowEngine, workflow_def: WorkflowDefinition) -> None:
        await engine.create_workflow(workflow_def, {})
        ok = await engine.resume()
        assert ok is False

    @pytest.mark.asyncio
    async def test_cancel_workflow(self, engine: WorkflowEngine, workflow_def: WorkflowDefinition) -> None:
        await engine.create_workflow(workflow_def, {})
        engine._state.status = WorkflowStatus.RUNNING
        ok = await engine.cancel(reason="user request")
        assert ok is True
        assert engine._state.status == WorkflowStatus.CANCELLED
        assert engine._state.error == "user request"
        assert engine._cancelled is True

    @pytest.mark.asyncio
    async def test_cancel_workflow_already_completed(
        self, engine: WorkflowEngine, workflow_def: WorkflowDefinition
    ) -> None:
        await engine.create_workflow(workflow_def, {})
        engine._state.status = WorkflowStatus.COMPLETED
        ok = await engine.cancel()
        assert ok is False

    @pytest.mark.asyncio
    async def test_retry_step(
        self, engine: WorkflowEngine, workflow_def: WorkflowDefinition
    ) -> None:
        await engine.create_workflow(workflow_def, {})
        step = self.make_step("agent1")
        orig = await engine.execute_step(step)
        assert orig.status == "completed"
        engine._state.failed_steps.append("agent1")
        retry_result = await engine.retry_step(orig.step_id)
        assert retry_result.status == "completed"
        assert retry_result.step_id != orig.step_id

    @pytest.mark.asyncio
    async def test_retry_step_not_found(self, engine: WorkflowEngine, workflow_def: WorkflowDefinition) -> None:
        await engine.create_workflow(workflow_def, {})
        with pytest.raises(ValueError, match="not found"):
            await engine.retry_step("nonexistent")

    @pytest.mark.asyncio
    async def test_retry_step_no_state(self, engine: WorkflowEngine) -> None:
        engine._state = None
        with pytest.raises(RuntimeError, match="No active workflow"):
            await engine.retry_step("anything")

    @pytest.mark.asyncio
    async def test_step_timeout(self, engine: WorkflowEngine, workflow_def: WorkflowDefinition) -> None:
        await engine.create_workflow(workflow_def, {})
        now = datetime.now(UTC)
        old_result = WorkflowStepResult(
            step_id="s_old",
            agent_id="agent1",
            status="running",
            started_at=now - timedelta(seconds=1000),
        )
        engine._state.step_results["s_old"] = old_result
        engine._workflow_def.timeout_seconds = 100
        engine._check_timeouts()
        assert engine._state.step_results["s_old"].status == "timed_out"
        assert "timed out" in engine._state.step_results["s_old"].error

    @pytest.mark.asyncio
    async def test_get_state(self, engine: WorkflowEngine, workflow_def: WorkflowDefinition) -> None:
        await engine.create_workflow(workflow_def, {})
        state = await engine.get_state()
        assert state is engine._state

    @pytest.mark.asyncio
    async def test_get_progress(self, engine: WorkflowEngine, workflow_def: WorkflowDefinition) -> None:
        await engine.create_workflow(workflow_def, {})
        progress = await engine.get_progress()
        assert progress == {"total_steps": 0, "completed_steps": 0, "failed_steps": 0, "percentage": 0.0}

    @pytest.mark.asyncio
    async def test_get_progress_with_steps(
        self, engine: WorkflowEngine, workflow_def: WorkflowDefinition
    ) -> None:
        await engine.create_workflow(workflow_def, {})
        engine._state.completed_steps = ["a", "b"]
        engine._state.failed_steps = ["c"]
        progress = await engine.get_progress()
        assert progress["total_steps"] == 3
        assert progress["completed_steps"] == 2
        assert progress["failed_steps"] == 1
        assert progress["percentage"] == 66.66666666666666

    @pytest.mark.asyncio
    async def test_execute_step_no_state(self, engine: WorkflowEngine) -> None:
        step = self.make_step("agent1")
        engine._state = None
        result = await engine.execute_step(step)
        assert result.status == "completed"
        assert result.agent_id == "agent1"

    @pytest.mark.asyncio
    async def test_execute_sequential_updates_status(
        self, engine: WorkflowEngine, workflow_def: WorkflowDefinition
    ) -> None:
        await engine.create_workflow(workflow_def, {})
        steps = [self.make_step("agent1")]
        await engine.execute_sequential(steps)
        assert engine.state.status == WorkflowStatus.RUNNING

    @pytest.mark.asyncio
    async def test_execute_step_agent_registry_error(
        self, workflow_def: WorkflowDefinition
    ) -> None:
        registry = MagicMock(spec=AgentRegistry)
        registry.get.side_effect = Exception("agent not found")
        tg = TaskGraph()
        engine = WorkflowEngine(task_graph=tg, agent_registry=registry)
        await engine.create_workflow(workflow_def, {})
        step = self.make_step("unknown_agent")
        result = await engine.execute_step(step)
        assert result.status == "failed"
        assert "agent not found" in result.error
