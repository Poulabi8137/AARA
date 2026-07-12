from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.research_memory import (
    MemoryImportance,
    MemorySource,
    SessionMemoryType,
    LongTermMemoryCategory,
    PaperMemoryType,
    ProjectMemoryCategory,
)


class UserResearchProfileCreate(BaseModel):
    expertise_areas: list[str] | None = None
    research_interests: list[str] | None = None
    preferred_methodologies: list[str] | None = None
    domains: list[str] | None = None
    skill_level: str | None = Field(None, max_length=64)
    preferences: dict[str, Any] | None = None


class UserResearchProfileUpdate(BaseModel):
    expertise_areas: list[str] | None = None
    research_interests: list[str] | None = None
    preferred_methodologies: list[str] | None = None
    domains: list[str] | None = None
    skill_level: str | None = Field(None, max_length=64)
    preferences: dict[str, Any] | None = None


class UserResearchProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    expertise_areas: list[str] | None
    research_interests: list[str] | None
    preferred_methodologies: list[str] | None
    domains: list[str] | None
    skill_level: str | None
    preferences: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionMemoryCreate(BaseModel):
    session_id: uuid.UUID
    user_id: uuid.UUID
    memory_type: SessionMemoryType
    content: str = Field(..., min_length=1)
    summary: str | None = None
    source: MemorySource = MemorySource.SYSTEM
    importance: MemoryImportance = MemoryImportance.MEDIUM
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    memory_metadata: dict[str, Any] | None = None


class SessionMemoryUpdate(BaseModel):
    content: str | None = Field(None, min_length=1)
    summary: str | None = None
    importance: MemoryImportance | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    memory_metadata: dict[str, Any] | None = None


class SessionMemoryResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    memory_type: SessionMemoryType
    content: str
    summary: str | None
    source: MemorySource
    importance: MemoryImportance
    confidence: float
    memory_metadata: dict[str, Any] | None
    embedding_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionMemoryListResponse(BaseModel):
    memories: list[SessionMemoryResponse]
    total: int


class LongTermMemoryCreate(BaseModel):
    user_id: uuid.UUID
    category: LongTermMemoryCategory
    content: str = Field(..., min_length=1)
    summary: str | None = None
    source_session_ids: list[str] | None = None
    importance: MemoryImportance = MemoryImportance.MEDIUM
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    memory_metadata: dict[str, Any] | None = None


class LongTermMemoryUpdate(BaseModel):
    content: str | None = Field(None, min_length=1)
    summary: str | None = None
    importance: MemoryImportance | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    memory_metadata: dict[str, Any] | None = None


class LongTermMemoryResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    category: LongTermMemoryCategory
    content: str
    summary: str | None
    source_session_ids: list[str] | None
    importance: MemoryImportance
    confidence: float
    memory_metadata: dict[str, Any] | None
    embedding_id: str | None
    consolidated_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LongTermMemoryListResponse(BaseModel):
    memories: list[LongTermMemoryResponse]
    total: int


class PaperMemoryCreate(BaseModel):
    project_id: uuid.UUID
    user_id: uuid.UUID
    memory_type: PaperMemoryType
    content: str = Field(..., min_length=1)
    document_id: uuid.UUID | None = None
    summary: str | None = None
    source_paper_title: str | None = Field(None, max_length=512)
    source_doi: str | None = Field(None, max_length=1024)
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0)
    memory_metadata: dict[str, Any] | None = None


class PaperMemoryResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    document_id: uuid.UUID | None
    user_id: uuid.UUID
    memory_type: PaperMemoryType
    content: str
    summary: str | None
    source_paper_title: str | None
    source_doi: str | None
    relevance_score: float
    memory_metadata: dict[str, Any] | None
    embedding_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaperMemoryListResponse(BaseModel):
    memories: list[PaperMemoryResponse]
    total: int


class ProjectMemoryCreate(BaseModel):
    project_id: uuid.UUID
    user_id: uuid.UUID
    category: ProjectMemoryCategory
    content: str = Field(..., min_length=1)
    summary: str | None = None
    importance: MemoryImportance = MemoryImportance.MEDIUM
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    memory_metadata: dict[str, Any] | None = None
    source_memory_ids: list[str] | None = None


class ProjectMemoryUpdate(BaseModel):
    content: str | None = Field(None, min_length=1)
    summary: str | None = None
    importance: MemoryImportance | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    memory_metadata: dict[str, Any] | None = None


class ProjectMemoryResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    category: ProjectMemoryCategory
    content: str
    summary: str | None
    importance: MemoryImportance
    confidence: float
    memory_metadata: dict[str, Any] | None
    embedding_id: str | None
    source_memory_ids: list[str] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectMemoryListResponse(BaseModel):
    memories: list[ProjectMemoryResponse]
    total: int


class SemanticMemoryIndexCreate(BaseModel):
    memory_type: str = Field(..., max_length=64)
    memory_id: uuid.UUID
    embedding_id: str = Field(..., max_length=128)
    collection_name: str = Field(..., max_length=128)
    content_hash: str = Field(..., max_length=64)
    user_id: uuid.UUID | None = None
    chunk_index: int | None = None
    memory_metadata: dict[str, Any] | None = None


class SemanticMemoryIndexUpdate(BaseModel):
    embedding_id: str | None = Field(None, max_length=128)
    collection_name: str | None = Field(None, max_length=128)
    memory_metadata: dict[str, Any] | None = None


class SemanticMemoryIndexResponse(BaseModel):
    id: uuid.UUID
    memory_type: str
    memory_id: uuid.UUID
    user_id: uuid.UUID | None
    embedding_id: str
    collection_name: str
    content_hash: str
    chunk_index: int | None
    memory_metadata: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SemanticMemoryIndexListResponse(BaseModel):
    indices: list[SemanticMemoryIndexResponse]
    total: int
