from __future__ import annotations

import uuid
from datetime import datetime, timezone
import enum

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RERUN_REQUESTED = "rerun_requested"


class HumanApproval(Base):
    __tablename__ = "human_approvals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_executions.id"), nullable=False
    )
    status: Mapped[ApprovalStatus] = mapped_column(
        SAEnum(ApprovalStatus, name="approval_status", create_constraint=True),
        default=ApprovalStatus.PENDING,
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(256), nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<HumanApproval id={self.id} execution={self.execution_id} status={self.status}>"
