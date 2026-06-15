from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AgentRunRequest(BaseModel):
    query: str
    project_id: str | None = None
    objective: str | None = None


class AgentRunResponse(BaseModel):
    execution_id: UUID
    status: str
    thread_id: str | None = None
    message: str = "Workflow started"


class AgentExecutionResponse(BaseModel):
    id: UUID
    project_id: UUID
    agent_name: str
    execution_status: str
    input_query: str | None = None
    output_report: str | None = None
    thread_id: str | None = None
    token_usage: dict[str, Any] | None = None
    node_durations: dict[str, Any] | None = None
    retry_count: int = 0
    error_message: str | None = None
    execution_metadata: dict[str, Any] | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    execution_log: str | None = None

    model_config = {"from_attributes": True}


class ExecutionListResponse(BaseModel):
    executions: list[AgentExecutionResponse]
    total: int


class CancelResponse(BaseModel):
    execution_id: UUID
    status: str
    message: str


class AgentInfoResponse(BaseModel):
    name: str
    description: str
    requires_human_approval: bool


class ExecutionStatusResponse(BaseModel):
    id: UUID
    execution_status: str
    thread_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    error_message: str | None = None


class AgentListResponse(BaseModel):
    agents: list[AgentInfoResponse]
