from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SAEnum, JSON, Integer, Float, Boolean, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.session import Base


class PaperStatus(str, enum.Enum):
    DRAFT = "draft"
    PROPOSAL = "proposal"
    PROPOSAL_COMPLETE = "proposal_complete"
    GENERATING = "generating"
    GENERATED = "generated"
    EDITING = "editing"
    REVIEWING = "reviewing"
    COMPLETE = "complete"
    FAILED = "failed"


class SectionStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"


class PaperOperation(str, enum.Enum):
    REWRITE = "rewrite"
    EXPAND = "expand"
    CONDENSE = "condense"
    IMPROVE_TONE = "improve_tone"
    REGENERATE = "regenerate"
    ADD_CITATIONS = "add_citations"
    IMPROVE_DEPTH = "improve_depth"


class EvidenceClass(str, enum.Enum):
    SUPPORTED = "supported"
    WEAKLY_SUPPORTED = "weakly_supported"
    NEEDS_CITATION = "needs_citation"
    SPECULATIVE = "speculative"


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_projects.id"), nullable=False)
    gap_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    proposed_title: Mapped[str] = mapped_column(String(512), nullable=False)
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    motivation: Mapped[str] = mapped_column(Text, nullable=False)
    research_questions: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    objectives: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    expected_contributions: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    proposed_methodology: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_strategy: Mapped[str] = mapped_column(Text, nullable=False)
    future_scope: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    domain: Mapped[str | None] = mapped_column(String(256), nullable=True)
    base_paper_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("ResearchProject", back_populates="proposals")
    papers = relationship("Paper", back_populates="proposal", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Proposal id={self.id} title={self.proposed_title[:50]}>"


class BasePaperAnalysis(Base):
    __tablename__ = "base_paper_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_projects.id"), nullable=False)
    source_doi: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    methodology: Mapped[str | None] = mapped_column(Text, nullable=True)
    dataset_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    experiments: Mapped[str | None] = mapped_column(Text, nullable=True)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    future_work: Mapped[str | None] = mapped_column(Text, nullable=True)
    references: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    originality_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    project = relationship("ResearchProject", back_populates="base_paper_analyses")

    def __repr__(self) -> str:
        return f"<BasePaperAnalysis id={self.id} source={self.source_doi or self.source_filename}>"


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research_projects.id"), nullable=False)
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("proposals.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    abstract: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    authors: Mapped[str] = mapped_column(String(1024), default="Placeholder Author")
    status: Mapped[PaperStatus] = mapped_column(SAEnum(PaperStatus, name="paper_status", create_constraint=True), default=PaperStatus.DRAFT, nullable=False)
    ieee_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("ResearchProject", back_populates="papers")
    proposal = relationship("Proposal", back_populates="papers")
    sections = relationship("PaperSection", back_populates="paper", cascade="all, delete-orphan", order_by="PaperSection.section_number")
    revisions = relationship("PaperRevision", back_populates="paper", cascade="all, delete-orphan", order_by="PaperRevision.created_at.desc()")
    citations = relationship("PaperCitation", back_populates="paper", cascade="all, delete-orphan")
    exports = relationship("PaperExport", back_populates="paper", cascade="all, delete-orphan")
    metrics = relationship("PaperMetrics", back_populates="paper", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Paper id={self.id} title={self.title[:50]}>"


class PaperSection(Base):
    __tablename__ = "paper_sections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False)
    section_number: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[SectionStatus] = mapped_column(SAEnum(SectionStatus, name="section_status", create_constraint=True), default=SectionStatus.DRAFT, nullable=False)
    evidence_classifications: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    paper = relationship("Paper", back_populates="sections")

    def __repr__(self) -> str:
        return f"<PaperSection id={self.id} n={self.section_number} title={self.section_title}>"


class PaperRevision(Base):
    __tablename__ = "paper_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False)
    section_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("paper_sections.id"), nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    operation: Mapped[PaperOperation] = mapped_column(SAEnum(PaperOperation, name="paper_operation", create_constraint=True), nullable=False)
    old_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    paper = relationship("Paper", back_populates="revisions")
    section = relationship("PaperSection")

    def __repr__(self) -> str:
        return f"<PaperRevision id={self.id} op={self.operation.value}>"


class PaperCitation(Base):
    __tablename__ = "paper_citations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False)
    citation_key: Mapped[str] = mapped_column(String(128), nullable=False)
    authors: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    title: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    journal: Mapped[str | None] = mapped_column(String(512), nullable=True)
    volume: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pages: Mapped[str | None] = mapped_column(String(64), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(256), nullable=True)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    ieee_format: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_errors: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    paper = relationship("Paper", back_populates="citations")

    def __repr__(self) -> str:
        return f"<PaperCitation key={self.citation_key} verified={self.verified}>"


class PaperExport(Base):
    __tablename__ = "paper_exports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    paper = relationship("Paper", back_populates="exports")

    def __repr__(self) -> str:
        return f"<PaperExport id={self.id} format={self.format}>"


class PaperMetrics(Base):
    __tablename__ = "paper_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False, unique=True)
    novelty_score: Mapped[float] = mapped_column(Float, default=0.0)
    citation_coverage: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_strength: Mapped[float] = mapped_column(Float, default=0.0)
    methodology_quality: Mapped[float] = mapped_column(Float, default=0.0)
    writing_quality: Mapped[float] = mapped_column(Float, default=0.0)
    logical_consistency: Mapped[float] = mapped_column(Float, default=0.0)
    academic_tone: Mapped[float] = mapped_column(Float, default=0.0)
    section_completeness: Mapped[float] = mapped_column(Float, default=0.0)
    composite_score: Mapped[float] = mapped_column(Float, default=0.0)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    suggestions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    paper = relationship("Paper", back_populates="metrics")

    def __repr__(self) -> str:
        return f"<PaperMetrics id={self.id} composite={self.composite_score:.1f}>"


class EvidenceStatement(Base):
    __tablename__ = "evidence_statements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False)
    section_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("paper_sections.id"), nullable=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[EvidenceClass] = mapped_column(SAEnum(EvidenceClass, name="evidence_class", create_constraint=True), nullable=False)
    citation_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    paper = relationship("Paper")
    section = relationship("PaperSection")

    def __repr__(self) -> str:
        return f"<EvidenceStatement id={self.id} class={self.classification.value}>"
