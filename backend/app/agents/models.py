from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentStatus(enum.StrEnum):
    INITIALIZED = "initialized"
    RECEIVING_CONTEXT = "receiving_context"
    PLANNING = "planning"
    REASONING = "reasoning"
    REQUESTING_TOOL = "requesting_tool"
    EXECUTING_TOOL = "executing_tool"
    OBSERVING_RESULT = "observing_result"
    REFLECTING = "reflecting"
    SELF_VALIDATING = "self_validating"
    OUTPUTTING_RESULT = "outputting_result"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ERROR = "error"


class AgentPhase(enum.StrEnum):
    IDLE = "idle"
    PLANNING = "planning"
    REASONING = "reasoning"
    TOOL_USE = "tool_use"
    REFLECTING = "reflecting"
    VALIDATING = "validating"
    OUTPUTTING = "outputting"


class AgentContext(BaseModel):
    workflow_id: str
    step_id: str
    trace_id: str
    input: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConfidenceScore(BaseModel):
    overall: float = 0.0
    citation_support: float = 0.0
    factual_grounding: float = 0.0
    reasoning_coherence: float = 0.0


class AgentOutput(BaseModel):
    agent_id: str
    workflow_id: str
    output: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    duration_ms: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    confidence: ConfidenceScore = Field(default_factory=ConfidenceScore)


class ReasoningStep(BaseModel):
    step_number: int
    description: str
    result: str = ""


class ToolCall(BaseModel):
    tool_id: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = 0


class Observation(BaseModel):
    source: str
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class Reflection(BaseModel):
    insight: str
    confidence: float = 1.0
    source: str = ""


class AgentStep(BaseModel):
    agent_id: str
    input: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] | None = None
    priority: int = 0
    depends_on: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    timeout_seconds: int = 60
    max_retries: int = 3
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionPlan(BaseModel):
    steps: list[AgentStep] = Field(default_factory=list)
    parallel_branches: list[list[AgentStep]] = Field(default_factory=list)
    estimated_cost: dict[str, float] = Field(default_factory=dict)
    requires_approval: list[str] = Field(default_factory=list)


class AgentState(BaseModel):
    agent_id: str
    workflow_id: str
    step_id: str = ""
    status: AgentStatus = AgentStatus.INITIALIZED
    current_phase: AgentPhase = AgentPhase.IDLE
    retry_count: int = 0
    max_retries: int = 3
    plan: str | None = None
    reasoning_history: list[ReasoningStep] = Field(default_factory=list)
    tool_call_history: list[ToolCall] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    reflections: list[Reflection] = Field(default_factory=list)
    accumulated_context: list[dict[str, Any]] = Field(default_factory=list)
    context_token_count: int = 0
    max_context_tokens: int = 32000
    intermediate_outputs: dict[str, Any] = Field(default_factory=dict)
    final_output: AgentOutput | None = None
    started_at: datetime | None = None
    current_step_started_at: datetime | None = None
    total_duration_ms: int = 0


class AgentMetadata(BaseModel):
    id: str
    name: str
    version: str = "1.0"


class WorkflowResult(BaseModel):
    workflow_id: str
    status: str
    query: str = ""
    execution_plan: ExecutionPlan | None = None
    papers: Any | None = None
    analysis: Any | None = None
    ideas: Any | None = None
    draft: Any | None = None
    review: Any | None = None
    costs: dict[str, float] = Field(default_factory=dict)
    duration_ms: int = 0
    steps_completed: list[str] = Field(default_factory=list)
    steps_failed: list[str] = Field(default_factory=list)
    checkpoint_decisions: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
