from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.db.session import Base


class SessionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_projects.id"), nullable=False
    )
    session_name: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        SAEnum(SessionStatus, name="session_status", create_constraint=True),
        default=SessionStatus.PENDING,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    project = relationship("ResearchProject", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<ResearchSession id={self.id} name={self.session_name} status={self.status}>"
