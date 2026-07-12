from __future__ import annotations

import uuid
from datetime import datetime, timezone
import enum

from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SAEnum, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_projects.id"), nullable=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    collection: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus, name="document_status", create_constraint=True),
        default=DocumentStatus.PENDING,
        nullable=False,
    )
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    author: Mapped[str | None] = mapped_column(String(256), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    paper_memories = relationship("PaperMemory", back_populates="document")

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename} status={self.status}>"
