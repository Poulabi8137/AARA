from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class ExecutionType(enum.StrEnum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    DEPENDENCY = "dependency"


class WorkflowStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


@dataclass
class WorkflowDefinition:
    workflow_type: str
    description: str = ""
    agents: list[str] = field(default_factory=list)
    handler: type | None = None
    execution_type: ExecutionType = ExecutionType.SEQUENTIAL
    timeout_seconds: int = 300
    max_retries: int = 3
    checkpoint_phases: list[str] = field(default_factory=list)


@dataclass
class WorkflowStepResult:
    step_id: str
    agent_id: str
    status: str
    output: Any | None = None
    error: str | None = None
    duration_ms: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class WorkflowState:
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step: str = ""
    completed_steps: list[str] = field(default_factory=list)
    failed_steps: list[str] = field(default_factory=list)
    step_results: dict[str, WorkflowStepResult] = field(default_factory=dict)
    start_time: datetime | None = None
    end_time: datetime | None = None
    error: str | None = None
    checkpoint_data: dict[str, Any] = field(default_factory=dict)
