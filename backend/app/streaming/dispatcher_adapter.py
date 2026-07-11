from __future__ import annotations

from typing import Any

from app.streaming.events import AgentEvent, BaseEvent, EventType, WorkflowEvent
from app.streaming.manager import EventStreamManager


class StreamEventDispatcher:
    """Implements the dispatch_* interface SupervisorAgent expects, backed by
    EventStreamManager — so events SupervisorAgent emits actually land where
    DashboardService reads them from."""

    def __init__(self, event_manager: EventStreamManager) -> None:
        self._event_manager = event_manager

    async def dispatch_workflow_started(
        self,
        workflow_id: str,
        workflow_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await self._event_manager.publish_event(WorkflowEvent(
            type=EventType.WORKFLOW_STARTED,
            workflow_id=workflow_id,
            status="running",
            data={"workflow_type": workflow_type, **(metadata or {})},
        ))

    async def dispatch_workflow_completed(
        self, workflow_id: str, result: dict[str, Any] | None = None,
    ) -> None:
        await self._event_manager.publish_event(WorkflowEvent(
            type=EventType.WORKFLOW_COMPLETED,
            workflow_id=workflow_id,
            status="completed",
            data=result or {},
        ))

    async def dispatch_workflow_failed(self, workflow_id: str, error: str) -> None:
        await self._event_manager.publish_event(WorkflowEvent(
            type=EventType.WORKFLOW_FAILED,
            workflow_id=workflow_id,
            status="failed",
            error=error,
            data={"error": error},
        ))

    async def dispatch_agent_started(self, agent_id: str, workflow_id: str) -> None:
        await self._event_manager.publish_event(AgentEvent(
            type=EventType.AGENT_STARTED,
            workflow_id=workflow_id,
            agent_id=agent_id,
            status="running",
        ))

    async def dispatch_agent_completed(
        self, agent_id: str, workflow_id: str, output: dict[str, Any] | None = None,
    ) -> None:
        await self._event_manager.publish_event(AgentEvent(
            type=EventType.AGENT_COMPLETED,
            workflow_id=workflow_id,
            agent_id=agent_id,
            status="completed",
            data=output or {},
        ))

    async def dispatch_agent_failed(self, agent_id: str, workflow_id: str, error: str) -> None:
        await self._event_manager.publish_event(AgentEvent(
            type=EventType.AGENT_FAILED,
            workflow_id=workflow_id,
            agent_id=agent_id,
            status="failed",
            error=error,
            data={"error": error},
        ))

    async def dispatch_progress(
        self,
        workflow_id: str,
        step_id: str,
        agent_id: str,
        percentage: float,
        message: str,
    ) -> None:
        await self._event_manager.publish_progress(
            workflow_id, step_id, agent_id, percentage, message,
        )

    async def dispatch_checkpoint_created(
        self, workflow_id: str, phase: str, checkpoint_id: str, output_summary: str,
    ) -> None:
        await self._event_manager.publish_event(BaseEvent(
            type=EventType.CHECKPOINT_CREATED,
            workflow_id=workflow_id,
            data={
                "phase": phase,
                "checkpoint_id": checkpoint_id,
                "output_summary": output_summary,
            },
        ))

    async def dispatch_evaluation_result(
        self, workflow_id: str, metric_name: str, score: float, details: str = "",
    ) -> None:
        await self._event_manager.publish_event(BaseEvent(
            type=EventType.METRIC_COLLECTED,
            workflow_id=workflow_id,
            data={"evaluation": {"metric": metric_name, "score": score, "details": details}},
        ))

    async def dispatch_error(
        self, source: str, error: str, context: dict[str, Any] | None = None,
    ) -> None:
        await self._event_manager.publish_event(BaseEvent(
            type=EventType.ERROR,
            workflow_id=(context or {}).get("workflow_id", ""),
            data={"source": source, "error": error, "context": context or {}},
        ))
