from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.document import DocumentStatus


class DocumentResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID | None
    filename: str
    collection: str
    status: DocumentStatus
    chunk_count: int | None
    char_count: int | None
    author: str | None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class DocumentCreate(BaseModel):
    filename: str
    content_type: str
    file_size: int
    extension: str


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    collection: str | None = Field(None, description="Restrict to a single collection")
    project_id: str | None = None
    top_k: int = Field(10, ge=1, le=100)


class SearchResultItem(BaseModel):
    content: str
    source: str
    score: float
    metadata: dict
    chunk_id: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    total: int
    collection: str | None


class ContextRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    project_id: str | None = None
    top_k: int = Field(10, ge=1, le=100)
    collections: list[str] | None = None


class ContextResponse(BaseModel):
    query: str
    collections: dict[str, list[SearchResultItem]]
    total: int
