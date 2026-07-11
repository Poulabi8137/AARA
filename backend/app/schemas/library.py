from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PaperUploadResponse(BaseModel):
    id: str
    title: str
    file_type: str
    file_size: int | None = None
    status: str
    version: int = 1
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class PaperUpdate(BaseModel):
    title: str | None = None
    authors: list[str] | None = None
    abstract: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    url: str | None = None
    publication_year: int | None = None
    venue: str | None = None


class PaperResponse(BaseModel):
    id: str
    workspace_id: str
    project_id: str | None = None
    title: str
    authors: list[str] | None = None
    abstract: str | None = None
    source: str | None = None
    file_path: str | None = None
    file_type: str | None = None
    file_size: int | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    url: str | None = None
    publication_year: int | None = None
    venue: str | None = None
    citation_count: int = 0
    status: str | None = None
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class PaperCreate(BaseModel):
    workspace_id: str
    title: str
    authors: list[str] | None = None
    abstract: str | None = None
    doi: str | None = None
    url: str | None = None
    publication_year: int | None = None


class PaperVersionResponse(BaseModel):
    version: int
    file_type: str | None = None
    file_size: int | None = None
    created_at: datetime | None = None


class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool
    existing_paper: PaperResponse | None = None
    confidence: float
