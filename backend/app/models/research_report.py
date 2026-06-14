from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.db.session import Base


class ReportType(str, enum.Enum):
    ACADEMIC = "academic"
    EXECUTIVE = "executive"
    COMPREHENSIVE = "comprehensive"


class ResearchReport(Base):
    __tablename__ = "research_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_projects.id"), nullable=False
    )
    report_type: Mapped[ReportType] = mapped_column(
        SAEnum(ReportType, name="report_type", create_constraint=True),
        default=ReportType.ACADEMIC,
        nullable=False,
    )
    report_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    project = relationship("ResearchProject", back_populates="reports")

    def __repr__(self) -> str:
        return f"<ResearchReport id={self.id} type={self.report_type}>"
