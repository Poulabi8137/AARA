from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_projects.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    workflow_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    query: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_phases_completed: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Per-phase agent output, keyed by phase name (e.g. "analysis", "writing",
    # "idea_generation"). Populated by trigger_retrieval/analysis/writing in
    # research_service.py — previously the agent's AgentOutput was discarded
    # after execute(), so gap-analysis/idea-generation results were computed
    # but never persisted or retrievable via the API.
    results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    project = relationship("ResearchProject", back_populates="sessions")
    documents = relationship("Document", back_populates="session")
