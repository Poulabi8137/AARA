from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    theme: Mapped[str] = mapped_column(String(10), default="system")
    default_llm_provider: Mapped[str] = mapped_column(String(50), default="openai")
    default_embedding_model: Mapped[str] = mapped_column(
        String(200), default="sentence-transformers/all-MiniLM-L6-v2"
    )
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    preferences: Mapped[dict[str, object] | None] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    user = relationship("User", back_populates="preferences")
