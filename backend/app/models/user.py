from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Enum as SAEnum, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
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
    research_profile = relationship(
        "UserResearchProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    session_memories = relationship("SessionMemory", back_populates="user")
    long_term_memories = relationship("LongTermMemory", back_populates="user")
    paper_memories = relationship("PaperMemory", back_populates="user")
    project_memories = relationship("ProjectMemory", back_populates="user")
    semantic_memory_indices = relationship("SemanticMemoryIndex", back_populates="user")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
