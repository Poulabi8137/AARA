from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.db.session import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    RESEARCHER = "researcher"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", create_constraint=True),
        default=UserRole.RESEARCHER,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    projects = relationship("ResearchProject", back_populates="creator")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
