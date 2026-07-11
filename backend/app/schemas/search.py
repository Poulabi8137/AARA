from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    scope: Literal["workspace", "papers", "citations", "projects", "semantic"]
    workspace_id: str | None = None
    project_id: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    filters: dict | None = None


class SearchResult(BaseModel):
    id: str
    type: Literal["paper", "citation", "project", "workspace", "document"]
    title: str
    snippet: str
    score: float
    metadata: dict = {}


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    page: int
    page_size: int
    total_pages: int
