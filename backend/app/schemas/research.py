from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ResearchSessionCreate(BaseModel):
    project_id: str
    query: str


class ResearchSessionResponse(BaseModel):
    id: str
    project_id: str
    status: str
    workflow_id: str | None = None
    query: str
    agent_phases_completed: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    results: dict | None = None

    model_config = {"from_attributes": True}


class ResearchProjectCreate(BaseModel):
    workspace_id: str
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    research_goal: str | None = None
    key_questions: list[str] | None = None


class ResearchProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    research_goal: str | None = None
    key_questions: list[str] | None = None
    status: Literal["active", "archived"] | None = None


class ResearchProjectResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: str | None = None
    status: str = "active"
    research_goal: str | None = None
    key_questions: list[str] | None = None
    session_count: int = 0
    paper_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ResearchSubmission(BaseModel):
    query: str
    project_id: str
    max_papers: int = 50
    research_direction: str | None = None


class ResearchSubmissionResponse(BaseModel):
    session_id: str
    workflow_id: str
    status: str
    message: str
