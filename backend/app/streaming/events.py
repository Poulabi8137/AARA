from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


class EventType(enum.StrEnum):
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    AGENT_RETRYING = "agent.retrying"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_PAUSED = "workflow.paused"
    WORKFLOW_RESUMED = "workflow.resumed"
    WORKFLOW_CANCELLED = "workflow.cancelled"
    PROGRESS_UPDATED = "progress.updated"
    TOKEN_STREAM = "token.stream"
    CHECKPOINT_CREATED = "checkpoint.created"
    CHECKPOINT_RESOLVED = "checkpoint.resolved"
    METRIC_COLLECTED = "metric.collected"
    ERROR = "error"


@dataclass
class BaseEvent:
    event_id: str = ""
    type: EventType = EventType.ERROR
    workflow_id: str = ""
    timestamp: datetime | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = str(uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC)


@dataclass
class AgentEvent(BaseEvent):
    agent_id: str = ""
    agent_name: str = ""
    status: str = ""
    output_summary: str | None = None
    error: str | None = None
    duration_ms: int | None = None


@dataclass
class WorkflowEvent(BaseEvent):
    status: str = ""
    current_phase: str = ""
    completed_steps: int = 0
    total_steps: int = 0
    error: str | None = None


@dataclass
class ProgressEvent(BaseEvent):
    step_id: str = ""
    agent_id: str = ""
    percentage: float = 0.0
    message: str = ""


@dataclass
class TokenStreamEvent(BaseEvent):
    agent_id: str = ""
    content: str = ""
    finish_reason: str | None = None
