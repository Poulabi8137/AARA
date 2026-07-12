from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
    JSON,
    Integer,
    UUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.session import Base
from app.core.logging import get_logger

logger = get_logger("models.agent_execution")


class ExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_projects.id"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(String(256), nullable=False)
    execution_status: Mapped[ExecutionStatus] = mapped_column(
        SAEnum(ExecutionStatus, name="execution_status", create_constraint=True),
        default=ExecutionStatus.PENDING,
        nullable=False,
    )
    start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    execution_log: Mapped[str | None] = mapped_column(Text, nullable=True)

    input_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    thread_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    token_usage: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    node_durations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    project = relationship("ResearchProject", back_populates="agent_executions")

    def __repr__(self) -> str:
        return f"<AgentExecution id={self.id} agent={self.agent_name} status={self.execution_status}>"
