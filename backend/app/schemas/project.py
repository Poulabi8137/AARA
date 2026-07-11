from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    workspace_id: str
    name: str
    description: str | None = None
    research_question: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    research_question: str | None = None
    status: str | None = None


class ProjectResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: str | None = None
    research_question: str | None = None
    status: str = "active"
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
