from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DocumentGenerateRequest(BaseModel):
    workspace_id: str
    session_id: str | None = None
    project_id: str | None = None
    format: Literal["markdown", "docx", "pdf", "html"]
    title: str
    template: str | None = None
    sections: list[str] | None = None


class DocumentResponse(BaseModel):
    id: str
    workspace_id: str
    session_id: str | None = None
    format: str
    title: str
    content: str | None = None
    file_path: str | None = None
    file_size: int | None = None
    status: str
    version: int = 1
    citation_count: int = 0
    template_used: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class DocumentCreate(BaseModel):
    workspace_id: str
    title: str
    format: Literal["markdown", "docx", "pdf", "html"] = "markdown"
    session_id: str | None = None
    project_id: str | None = None


class DocumentUpdate(BaseModel):
    title: str | None = None
    content: str | None = None


class DocumentExportRequest(BaseModel):
    format: Literal["markdown", "docx", "pdf", "html"]


class DocumentExportResponse(BaseModel):
    format: str
    content: str
    filename: str
    mime_type: str | None = None
