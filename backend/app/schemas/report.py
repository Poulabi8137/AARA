from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.research_report import ReportType


class ReportCreate(BaseModel):
    project_id: uuid.UUID
    report_type: ReportType = ReportType.ACADEMIC
    report_path: str = Field(..., max_length=1024)


class ReportResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    report_type: ReportType
    report_path: str
    generated_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    reports: list[ReportResponse]
    total: int
