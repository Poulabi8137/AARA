from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CitationCreate(BaseModel):
    paper_id: str | None = None
    style: str = "apa"
    authors: list[str] | None = None
    title: str = Field(min_length=1)
    year: int | None = None
    journal: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    url: str | None = None
    isbn: str | None = None
    publisher: str | None = None
    source_type: str = "journal"


class CitationUpdate(BaseModel):
    paper_id: str | None = None
    style: str | None = None
    authors: list[str] | None = None
    title: str | None = None
    year: int | None = None
    journal: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    url: str | None = None
    isbn: str | None = None
    publisher: str | None = None
    source_type: str | None = None


class CitationResponse(BaseModel):
    id: str
    workspace_id: str
    paper_id: str | None = None
    raw_citation_text: str | None = None
    formatted_citation: str | None = None
    style: str = "apa"
    source_type: str = "journal"
    authors: list[str] | None = None
    title: str | None = None
    year: int | None = None
    journal: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    url: str | None = None
    isbn: str | None = None
    publisher: str | None = None
    accessed_date: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class CitationExportRequest(BaseModel):
    citation_ids: list[str]
    format: Literal["bibtex", "ris", "apa", "mla", "ieee"]


class CitationExportResponse(BaseModel):
    format: str
    content: str
    filename: str


class CitationLibrarySummary(BaseModel):
    total_citations: int
    by_style: dict[str, int]
    by_source_type: dict[str, int]
