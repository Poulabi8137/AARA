from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SAEnum, JSON, Float, Integer, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.session import Base


class MemoryImportance(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MemorySource(str, enum.Enum):
    AGENT = "agent"
    USER = "user"
    PAPER = "paper"
    SYSTEM = "system"
    EXTERNAL = "external"


class SessionMemoryType(str, enum.Enum):
    CONVERSATION = "conversation"
    FINDING = "finding"
    OBSERVATION = "observation"
    INSIGHT = "insight"
    QUERY = "query"
    AGENT_OUTPUT = "agent_output"
    DECISION = "decision"


class LongTermMemoryCategory(str, enum.Enum):
    RESEARCH_PATTERN = "research_pattern"
    METHODOLOGY_PREFERENCE = "methodology_preference"
    DOMAIN_KNOWLEDGE = "domain_knowledge"
    USER_PREFERENCE = "user_preference"
    CROSS_SESSION_INSIGHT = "cross_session_insight"
    REUSABLE_FINDING = "reusable_finding"


class PaperMemoryType(str, enum.Enum):
    KEY_FINDING = "key_finding"
    METHODOLOGY = "methodology"
    LIMITATION = "limitation"
    CITATION_INSIGHT = "citation_insight"
    FUTURE_WORK = "future_work"
    DATASET_NOTE = "dataset_note"
    EXPERIMENT_NOTE = "experiment_note"


class ProjectMemoryCategory(str, enum.Enum):
    RESEARCH_DIRECTION = "research_direction"
    METHODOLOGY_DECISION = "methodology_decision"
    AGGREGATED_INSIGHT = "aggregated_insight"
    EXPERIMENT_RESULT = "experiment_result"
    HYPOTHESIS = "hypothesis"
    KNOWLEDGE_GAP = "knowledge_gap"


class UserResearchProfile(Base):
    __tablename__ = "research_user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    expertise_areas: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    research_interests: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    preferred_methodologies: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    domains: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    skill_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    preferences: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="research_profile")

    def __repr__(self) -> str:
        return f"<UserResearchProfile id={self.id} user_id={self.user_id}>"


class SessionMemory(Base):
    __tablename__ = "session_memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_sessions.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    memory_type: Mapped[SessionMemoryType] = mapped_column(SAEnum(SessionMemoryType, name="session_memory_type", create_constraint=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[MemorySource] = mapped_column(SAEnum(MemorySource, name="memory_source", create_constraint=True), default=MemorySource.SYSTEM, nullable=False)
    importance: Mapped[MemoryImportance] = mapped_column(SAEnum(MemoryImportance, name="memory_importance", create_constraint=True), default=MemoryImportance.MEDIUM, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    memory_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session = relationship("ResearchSession", back_populates="session_memories")
    user = relationship("User", back_populates="session_memories")

    def __repr__(self) -> str:
        return f"<SessionMemory id={self.id} type={self.memory_type.value} importance={self.importance.value}>"


class LongTermMemory(Base):
    __tablename__ = "long_term_memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    category: Mapped[LongTermMemoryCategory] = mapped_column(SAEnum(LongTermMemoryCategory, name="long_term_memory_category", create_constraint=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_session_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    importance: Mapped[MemoryImportance] = mapped_column(SAEnum(MemoryImportance, name="long_term_memory_importance", create_constraint=True), default=MemoryImportance.MEDIUM, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    memory_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    consolidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="long_term_memories")

    def __repr__(self) -> str:
        return f"<LongTermMemory id={self.id} category={self.category.value} importance={self.importance.value}>"


class PaperMemory(Base):
    __tablename__ = "paper_memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_projects.id"), nullable=False, index=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    memory_type: Mapped[PaperMemoryType] = mapped_column(SAEnum(PaperMemoryType, name="paper_memory_type", create_constraint=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_paper_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_doi: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=1.0)
    memory_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    project = relationship("ResearchProject", back_populates="paper_memories")
    document = relationship("Document", back_populates="paper_memories")
    user = relationship("User", back_populates="paper_memories")

    def __repr__(self) -> str:
        return f"<PaperMemory id={self.id} type={self.memory_type.value} relevance={self.relevance_score}>"


class ProjectMemory(Base):
    __tablename__ = "project_memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_projects.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    category: Mapped[ProjectMemoryCategory] = mapped_column(SAEnum(ProjectMemoryCategory, name="project_memory_category", create_constraint=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    importance: Mapped[MemoryImportance] = mapped_column(SAEnum(MemoryImportance, name="project_memory_importance", create_constraint=True), default=MemoryImportance.MEDIUM, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    memory_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_memory_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("ResearchProject", back_populates="project_memories")
    user = relationship("User", back_populates="project_memories")

    def __repr__(self) -> str:
        return f"<ProjectMemory id={self.id} category={self.category.value} importance={self.importance.value}>"


class SemanticMemoryIndex(Base):
    __tablename__ = "semantic_memory_indices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    memory_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    embedding_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    collection_name: Mapped[str] = mapped_column(String(128), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    chunk_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="semantic_memory_indices")

    def __repr__(self) -> str:
        return f"<SemanticMemoryIndex id={self.id} type={self.memory_type} embedding={self.embedding_id}>"
