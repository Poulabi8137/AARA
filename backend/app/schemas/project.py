from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.research_project import ProjectStatus


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    description: str | None = Field(None, max_length=10000)


class ProjectUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=512)
    description: str | None = Field(None, max_length=10000)
    status: ProjectStatus | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    status: ProjectStatus
    created_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int
