from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from app.agents.models import AgentStep
from app.agents.task_graph import TaskGraph
from app.plugins.agent_registry import AgentRegistry
from app.workflow.types import (
    WorkflowDefinition,
    WorkflowState,
    WorkflowStatus,
    WorkflowStepResult,
)

if TYPE_CHECKING:
    from app.approval.human import HumanApprovalManager


class WorkflowEngine:
    def __init__(
        self,
        task_graph: TaskGraph,
        agent_registry: AgentRegistry | None = None,
        approval_manager: HumanApprovalManager | None = None,
    ) -> None:
        self._task_graph = task_graph
        self._agent_registry = agent_registry or AgentRegistry()
        self._approval_manager = approval_manager
        self._state: WorkflowState | None = None
        self._workflow_def: WorkflowDefinition | None = None
        self._input_data: dict[str, Any] = {}
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._cancelled = False
        self._current_task: asyncio.Task[Any] | None = None

    @property
    def state(self) -> WorkflowState | None:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._state is not None and self._state.status == WorkflowStatus.RUNNING

    @property
    def is_paused(self) -> bool:
        return self._state is not None and self._state.status == WorkflowStatus.PAUSED

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    async def create_workflow(self, workflow_def: WorkflowDefinition, input_data: dict[str, Any]) -> str:  # noqa: E501
        workflow_id = f"wf_{uuid4().hex[:12]}"
        self._workflow_def = workflow_def
        self._input_data = input_data
        self._state = WorkflowState(
            workflow_id=workflow_id,
            status=WorkflowStatus.PENDING,
            start_time=datetime.now(UTC),
        )
        return workflow_id

    async def execute_sequential(self, steps: list[AgentStep]) -> list[WorkflowStepResult]:
        results: list[WorkflowStepResult] = []
        for step in steps:
            await self._pause_event.wait()
            if self._cancelled:
                break
            if self._state:
                self._state.current_step = step.agent_id
                self._state.status = WorkflowStatus.RUNNING
            result = await self.execute_step(step)
            results.append(result)
            if self._state and result.status == "failed":
                self._state.failed_steps.append(step.agent_id)
            elif self._state:
                self._state.completed_steps.append(step.agent_id)
        return results

    async def execute_parallel(self, steps: list[AgentStep]) -> list[WorkflowStepResult]:
        semaphore = asyncio.Semaphore(len(steps))
        async def run_step(step: AgentStep) -> WorkflowStepResult:
            async with semaphore:
                await self._pause_event.wait()
                if self._cancelled:
                    return WorkflowStepResult(
                        step_id=step.agent_id,
                        agent_id=step.agent_id,
                        status="cancelled",
                    )
                if self._state:
                    self._state.current_step = step.agent_id
                result = await self.execute_step(step)
                if self._state and result.status == "failed":
                    self._state.failed_steps.append(step.agent_id)
                elif self._state:
                    self._state.completed_steps.append(step.agent_id)
                return result

        tasks = [run_step(s) for s in steps]
        return await asyncio.gather(*tasks)

    async def execute_dependency(self, graph: TaskGraph) -> list[WorkflowStepResult]:
        completed: set[str] = set()
        results: list[WorkflowStepResult] = []

        while True:
            await self._pause_event.wait()
            if self._cancelled:
                break
            ready = graph.get_ready_steps(completed)
            if not ready:
                if graph.is_complete(completed):
                    break
                await asyncio.sleep(0.1)
                continue

            batch_results = await asyncio.gather(*[self.execute_step(s) for s in ready])
            for step, result in zip(ready, batch_results, strict=False):
                results.append(result)
                completed.add(step.agent_id)
                if self._state:
                    if result.status == "failed":
                        self._state.failed_steps.append(step.agent_id)
                    else:
                        self._state.completed_steps.append(step.agent_id)

            if self._state:
                self._check_timeouts()

        return results

    async def execute_step(self, step: AgentStep) -> WorkflowStepResult:
        started_at = datetime.now(UTC)
        step_id = f"step_{uuid4().hex[:8]}"
        try:
            agent = self._agent_registry.get(step.agent_id)
            agent.agent_id = step.agent_id
            output = await self._run_agent(agent, step)
            duration = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
            result = WorkflowStepResult(
                step_id=step_id,
                agent_id=step.agent_id,
                status="completed",
                output=output,
                duration_ms=duration,
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
        except Exception as exc:
            result = self._handle_step_error(step, exc, started_at)
        if self._state:
            self._state.step_results[step_id] = result
        return result

    async def _run_agent(self, agent: Any, step: AgentStep) -> Any:
        if hasattr(agent, "execute"):
            return await agent.execute(step.input)
        return {"status": "executed", "agent_id": step.agent_id}

    async def pause(self) -> bool:
        if self._state and self._state.status in (WorkflowStatus.RUNNING,):
            self._state.status = WorkflowStatus.PAUSED
            self._pause_event.clear()
            return True
        return False

    async def resume(self) -> bool:
        if self._state and self._state.status == WorkflowStatus.PAUSED:
            self._state.status = WorkflowStatus.RUNNING
            self._pause_event.set()
            return True
        return False

    async def cancel(self, reason: str = "") -> bool:
        if self._state and self._state.status in (
            WorkflowStatus.RUNNING,
            WorkflowStatus.PAUSED,
            WorkflowStatus.PENDING,
        ):
            self._cancelled = True
            self._state.status = WorkflowStatus.CANCELLED
            self._state.error = reason
            self._state.end_time = datetime.now(UTC)
            self._pause_event.set()
            if self._current_task and not self._current_task.done():
                self._current_task.cancel()
            return True
        return False

    async def retry_step(self, step_id: str) -> WorkflowStepResult:
        if not self._state:
            raise RuntimeError("No active workflow")
        step_result = self._state.step_results.get(step_id)
        if step_result is None:
            raise ValueError(f"Step result '{step_id}' not found")
        step = AgentStep(agent_id=step_result.agent_id)
        result = await self.execute_step(step)
        if result.status == "completed":
            self._state.failed_steps = [s for s in self._state.failed_steps if s != step_result.agent_id]  # noqa: E501
            self._state.completed_steps.append(step_result.agent_id)
        return result

    async def get_state(self) -> WorkflowState | None:
        return self._state

    async def get_progress(self) -> dict[str, Any]:
        if not self._state:
            return {"total_steps": 0, "completed_steps": 0, "failed_steps": 0, "percentage": 0.0}
        total = len(self._state.completed_steps) + len(self._state.failed_steps)
        completed = len(self._state.completed_steps)
        return {
            "total_steps": total,
            "completed_steps": completed,
            "failed_steps": len(self._state.failed_steps),
            "percentage": (completed / total * 100) if total > 0 else 0.0,
        }

    def _handle_step_error(self, step: AgentStep, error: Exception, started_at: datetime | None = None) -> WorkflowStepResult:  # noqa: E501
        if started_at is None:
            started_at = datetime.now(UTC)
        return WorkflowStepResult(
            step_id=f"step_{uuid4().hex[:8]}",
            agent_id=step.agent_id,
            status="failed",
            error=str(error),
            duration_ms=0,
            started_at=started_at,
            completed_at=datetime.now(UTC),
        )

    def _check_timeouts(self) -> None:
        if not self._state or not self._workflow_def:
            return
        now = datetime.now(UTC)
        for _step_id, result in list(self._state.step_results.items()):
            if result.status == "running" and result.started_at:
                elapsed = (now - result.started_at).total_seconds()
                step = AgentStep(agent_id=result.agent_id, timeout_seconds=self._workflow_def.timeout_seconds)  # noqa: E501
                if elapsed > step.timeout_seconds:
                    result.status = "timed_out"
                    result.error = f"Step timed out after {elapsed:.1f}s"
                    result.completed_at = now
                    self._state.failed_steps.append(result.agent_id)
