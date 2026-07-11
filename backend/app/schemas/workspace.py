from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    research_topic: str | None = None


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    research_topic: str | None = None
    status: Literal["active", "archived"] | None = None


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    research_topic: str | None = None
    status: str = "active"
    owner_id: str
    member_count: int = 0
    paper_count: int = 0
    workflow_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
