from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.research_memory import SessionMemory, MemoryImportance
from app.schemas.research_memory import SessionMemoryCreate, SessionMemoryUpdate
from app.vectorstore.memory_indexer import MemoryIndexer

logger = get_logger("services.research_memory.session_memory")


class SessionMemoryService:
    def __init__(self, db: AsyncSession, indexer: MemoryIndexer | None = None):
        self.db = db
        self._indexer = indexer

    async def get_memory(self, memory_id: uuid.UUID) -> SessionMemory:
        result = await self.db.execute(
            select(SessionMemory).where(SessionMemory.id == memory_id)
        )
        memory = result.scalar_one_or_none()
        if memory is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session memory not found",
            )
        return memory

    async def create_memory(self, data: SessionMemoryCreate) -> SessionMemory:
        memory = SessionMemory(
            session_id=data.session_id,
            user_id=data.user_id,
            memory_type=data.memory_type,
            content=data.content,
            summary=data.summary,
            source=data.source,
            importance=data.importance,
            confidence=data.confidence,
            memory_metadata=data.memory_metadata,
        )
        self.db.add(memory)
        await self.db.flush()
        logger.info(
            "created session memory",
            extra={
                "memory_id": str(memory.id),
                "session_id": str(data.session_id),
                "memory_type": data.memory_type.value,
            },
        )
        if self._indexer is not None:
            await self._indexer.index_session_memory(memory)
        return memory

    async def update_memory(
        self, memory_id: uuid.UUID, data: SessionMemoryUpdate
    ) -> SessionMemory:
        memory = await self.get_memory(memory_id)

        content_changed = data.content is not None
        if data.content is not None:
            memory.content = data.content
        if data.summary is not None:
            memory.summary = data.summary
        if data.importance is not None:
            memory.importance = data.importance
        if data.confidence is not None:
            memory.confidence = data.confidence
        if data.memory_metadata is not None:
            memory.memory_metadata = data.memory_metadata

        await self.db.flush()
        if self._indexer is not None and content_changed:
            await self._indexer.index_session_memory(memory)
        return memory

    async def delete_memory(self, memory_id: uuid.UUID) -> None:
        memory = await self.get_memory(memory_id)
        await self.db.delete(memory)
        await self.db.flush()
        logger.info("deleted session memory", extra={"memory_id": str(memory_id)})
        if self._indexer is not None:
            await self._indexer.remove_session_memory(memory_id)

    async def get_by_session(
        self, session_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[SessionMemory], int]:
        query = (
            select(SessionMemory)
            .where(SessionMemory.session_id == session_id)
            .order_by(SessionMemory.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count(SessionMemory.id)).where(
            SessionMemory.session_id == session_id
        )

        result = await self.db.execute(query)
        memories = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        return memories, total

    async def get_by_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[SessionMemory], int]:
        query = (
            select(SessionMemory)
            .where(SessionMemory.user_id == user_id)
            .order_by(SessionMemory.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count(SessionMemory.id)).where(
            SessionMemory.user_id == user_id
        )

        result = await self.db.execute(query)
        memories = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        return memories, total

    async def get_by_importance(
        self,
        user_id: uuid.UUID,
        importance: MemoryImportance,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[SessionMemory], int]:
        query = (
            select(SessionMemory)
            .where(
                and_(
                    SessionMemory.user_id == user_id,
                    SessionMemory.importance == importance,
                )
            )
            .order_by(SessionMemory.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count(SessionMemory.id)).where(
            and_(
                SessionMemory.user_id == user_id,
                SessionMemory.importance == importance,
            )
        )

        result = await self.db.execute(query)
        memories = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        return memories, total

    async def get_by_confidence(
        self,
        user_id: uuid.UUID,
        min_confidence: float = 0.0,
        max_confidence: float = 1.0,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[SessionMemory], int]:
        query = (
            select(SessionMemory)
            .where(
                and_(
                    SessionMemory.user_id == user_id,
                    SessionMemory.confidence >= min_confidence,
                    SessionMemory.confidence <= max_confidence,
                )
            )
            .order_by(SessionMemory.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count(SessionMemory.id)).where(
            and_(
                SessionMemory.user_id == user_id,
                SessionMemory.confidence >= min_confidence,
                SessionMemory.confidence <= max_confidence,
            )
        )

        result = await self.db.execute(query)
        memories = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        return memories, total
