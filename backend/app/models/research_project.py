from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SAEnum, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.session import Base


class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ResearchProject(Base):
    __tablename__ = "research_projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(ProjectStatus, name="project_status", create_constraint=True),
        default=ProjectStatus.DRAFT,
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    creator = relationship("User", back_populates="projects")
    sessions = relationship(
        "ResearchSession", back_populates="project", cascade="all, delete-orphan"
    )
    reports = relationship(
        "ResearchReport", back_populates="project", cascade="all, delete-orphan"
    )
    agent_executions = relationship(
        "AgentExecution", back_populates="project", cascade="all, delete-orphan"
    )
    proposals = relationship(
        "Proposal", back_populates="project", cascade="all, delete-orphan"
    )
    papers = relationship(
        "Paper", back_populates="project", cascade="all, delete-orphan"
    )
    base_paper_analyses = relationship(
        "BasePaperAnalysis", back_populates="project", cascade="all, delete-orphan"
    )
    project_memories = relationship(
        "ProjectMemory", back_populates="project", cascade="all, delete-orphan"
    )
    paper_memories = relationship(
        "PaperMemory", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ResearchProject id={self.id} title={self.title} status={self.status}>"
