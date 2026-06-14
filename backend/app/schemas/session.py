from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.research_session import SessionStatus


class SessionCreate(BaseModel):
    project_id: uuid.UUID
    session_name: str = Field(..., min_length=1, max_length=256)


class SessionResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    session_name: str
    status: SessionStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
    total: int
