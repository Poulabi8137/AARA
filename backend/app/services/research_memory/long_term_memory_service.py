from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.research_memory import LongTermMemory, LongTermMemoryCategory, MemoryImportance
from app.schemas.research_memory import LongTermMemoryCreate, LongTermMemoryUpdate
from app.vectorstore.memory_indexer import MemoryIndexer

logger = get_logger("services.research_memory.long_term_memory")


class LongTermMemoryService:
    def __init__(self, db: AsyncSession, indexer: MemoryIndexer | None = None):
        self.db = db
        self._indexer = indexer

    async def get_memory(self, memory_id: uuid.UUID) -> LongTermMemory:
        result = await self.db.execute(
            select(LongTermMemory).where(LongTermMemory.id == memory_id)
        )
        memory = result.scalar_one_or_none()
        if memory is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Long-term memory not found",
            )
        return memory

    async def store_memory(self, data: LongTermMemoryCreate) -> LongTermMemory:
        memory = LongTermMemory(
            user_id=data.user_id,
            category=data.category,
            content=data.content,
            summary=data.summary,
            source_session_ids=data.source_session_ids,
            importance=data.importance,
            confidence=data.confidence,
            memory_metadata=data.memory_metadata,
        )
        self.db.add(memory)
        await self.db.flush()
        logger.info(
            "stored long-term memory",
            extra={
                "memory_id": str(memory.id),
                "user_id": str(data.user_id),
                "category": data.category.value,
            },
        )
        if self._indexer is not None:
            await self._indexer.index_long_term_memory(memory)
        return memory

    async def update_memory(
        self, memory_id: uuid.UUID, data: LongTermMemoryUpdate
    ) -> LongTermMemory:
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
            await self._indexer.index_long_term_memory(memory)
        return memory

    async def archive_memory(self, memory_id: uuid.UUID) -> LongTermMemory:
        memory = await self.get_memory(memory_id)
        memory.importance = MemoryImportance.LOW
        memory.confidence = 0.0
        memory.memory_metadata = {
            **(memory.memory_metadata or {}),
            "archived": True,
            "archived_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.db.flush()
        logger.info("archived long-term memory", extra={"memory_id": str(memory_id)})
        if self._indexer is not None:
            await self._indexer.remove_long_term_memory(memory_id)
        return memory

    async def delete_memory(self, memory_id: uuid.UUID) -> None:
        memory = await self.get_memory(memory_id)
        await self.db.delete(memory)
        await self.db.flush()
        logger.info("deleted long-term memory", extra={"memory_id": str(memory_id)})
        if self._indexer is not None:
            await self._indexer.remove_long_term_memory(memory_id)

    async def merge_duplicates(
        self, memory_ids: list[uuid.UUID]
    ) -> LongTermMemory:
        if len(memory_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least two memory IDs are required for merging",
            )

        memories: list[LongTermMemory] = []
        for mid in memory_ids:
            memories.append(await self.get_memory(mid))

        primary = memories[0]
        duplicates = memories[1:]

        merged_source_ids: list[str] = list(primary.source_session_ids or [])
        merged_metadata: dict = dict(primary.memory_metadata or {})
        merged_confidence = primary.confidence

        for dup in duplicates:
            if dup.source_session_ids:
                for sid in dup.source_session_ids:
                    if sid not in merged_source_ids:
                        merged_source_ids.append(sid)
            if dup.memory_metadata:
                merged_metadata.update(dup.memory_metadata)
            merged_confidence = max(merged_confidence, dup.confidence)

            await self.db.delete(dup)

        primary.source_session_ids = merged_source_ids
        primary.memory_metadata = merged_metadata
        primary.confidence = merged_confidence
        primary.consolidated_at = datetime.now(timezone.utc)

        await self.db.flush()
        logger.info(
            "merged long-term memories",
            extra={
                "primary_id": str(primary.id),
                "merged_count": len(duplicates),
            },
        )
        if self._indexer is not None:
            for dup in duplicates:
                await self._indexer.remove_long_term_memory(dup.id)
            await self._indexer.index_long_term_memory(primary)
        return primary

    async def get_by_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[LongTermMemory], int]:
        query = (
            select(LongTermMemory)
            .where(LongTermMemory.user_id == user_id)
            .order_by(LongTermMemory.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count(LongTermMemory.id)).where(
            LongTermMemory.user_id == user_id
        )

        result = await self.db.execute(query)
        memories = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        return memories, total

    async def search_by_category(
        self,
        user_id: uuid.UUID,
        category: LongTermMemoryCategory,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[LongTermMemory], int]:
        query = (
            select(LongTermMemory)
            .where(
                and_(
                    LongTermMemory.user_id == user_id,
                    LongTermMemory.category == category,
                )
            )
            .order_by(LongTermMemory.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count(LongTermMemory.id)).where(
            and_(
                LongTermMemory.user_id == user_id,
                LongTermMemory.category == category,
            )
        )

        result = await self.db.execute(query)
        memories = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        return memories, total

    async def search_by_tags(
        self,
        user_id: uuid.UUID,
        tags: list[str],
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[LongTermMemory], int]:
        result = await self.db.execute(
            select(LongTermMemory)
            .where(LongTermMemory.user_id == user_id)
            .order_by(LongTermMemory.created_at.desc())
        )
        all_memories = list(result.scalars().all())

        tag_set = set(tags)
        matched = [
            m for m in all_memories
            if m.memory_metadata and isinstance(m.memory_metadata.get("tags"), list)
            and tag_set.intersection(m.memory_metadata["tags"])
        ]
        total = len(matched)
        paginated = matched[skip:skip + limit]

        return paginated, total
