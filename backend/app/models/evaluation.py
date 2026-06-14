from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_projects.id"), nullable=True
    )
    execution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_executions.id"), nullable=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    overall_quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    coverage_score: Mapped[float] = mapped_column(Float, default=0.0)
    citation_score: Mapped[float] = mapped_column(Float, default=0.0)
    hallucination_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    gap_score: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_strength_score: Mapped[float] = mapped_column(Float, default=0.0)
    source_diversity_score: Mapped[float] = mapped_column(Float, default=0.0)
    summary_quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    run_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    execution = relationship("AgentExecution", backref="evaluations")
    metrics = relationship("EvaluationMetric", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<EvaluationRun id={self.id} query={self.query[:50]}>"


class EvaluationMetric(Base):
    __tablename__ = "evaluation_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_runs.id"), nullable=False
    )
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    run = relationship("EvaluationRun", back_populates="metrics")


class EvaluationBenchmark(Base):
    __tablename__ = "evaluation_benchmarks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    expected_findings: Mapped[list] = mapped_column(JSON, nullable=False)
    expected_subtopics: Mapped[list] = mapped_column(JSON, nullable=False)
    expected_references: Mapped[list] = mapped_column(JSON, nullable=False)
    expected_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<EvaluationBenchmark id={self.id} name={self.name}>"
