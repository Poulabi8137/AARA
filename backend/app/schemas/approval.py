from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ApprovalCreate(BaseModel):
    workflow_id: str
    step_id: str
    artifact: dict[str, Any] | None = None


class ApprovalUpdate(BaseModel):
    decision: str  # "approved" | "rejected"
    feedback: str | None = None


class ApprovalResponse(BaseModel):
    id: str
    workflow_id: str
    step_id: str
    decision: str | None = None
    feedback: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
