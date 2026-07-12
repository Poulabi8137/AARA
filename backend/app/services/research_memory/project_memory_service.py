from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.research_memory import (
    ProjectMemory,
    ProjectMemoryCategory,
    MemoryImportance,
)
from app.schemas.research_memory import ProjectMemoryCreate, ProjectMemoryUpdate
from app.vectorstore.memory_indexer import MemoryIndexer

logger = get_logger("services.research_memory.project_memory")


class ProjectMemoryService:
    def __init__(self, db: AsyncSession, indexer: MemoryIndexer | None = None):
        self.db = db
        self._indexer = indexer

    async def get_memory(self, memory_id: uuid.UUID) -> ProjectMemory:
        result = await self.db.execute(
            select(ProjectMemory).where(ProjectMemory.id == memory_id)
        )
        memory = result.scalar_one_or_none()
        if memory is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project memory not found",
            )
        return memory

    async def create_memory(self, data: ProjectMemoryCreate) -> ProjectMemory:
        memory = ProjectMemory(
            project_id=data.project_id,
            user_id=data.user_id,
            category=data.category,
            content=data.content,
            summary=data.summary,
            importance=data.importance,
            confidence=data.confidence,
            memory_metadata=data.memory_metadata,
            source_memory_ids=data.source_memory_ids,
        )
        self.db.add(memory)
        await self.db.flush()
        logger.info(
            "created project memory",
            extra={
                "memory_id": str(memory.id),
                "project_id": str(data.project_id),
                "category": data.category.value,
            },
        )
        if self._indexer is not None:
            await self._indexer.index_project_memory(memory)
        return memory

    async def update_memory(
        self, memory_id: uuid.UUID, data: ProjectMemoryUpdate
    ) -> ProjectMemory:
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
            await self._indexer.index_project_memory(memory)
        return memory

    async def update_summary(
        self, memory_id: uuid.UUID, summary: str
    ) -> ProjectMemory:
        memory = await self.get_memory(memory_id)
        memory.summary = summary
        await self.db.flush()
        return memory

    async def delete_memory(self, memory_id: uuid.UUID) -> None:
        memory = await self.get_memory(memory_id)
        await self.db.delete(memory)
        await self.db.flush()
        logger.info("deleted project memory", extra={"memory_id": str(memory_id)})
        if self._indexer is not None:
            await self._indexer.remove_project_memory(memory_id)
    async def aggregate_memories(
        self,
        project_id: uuid.UUID,
        source_ids: list[uuid.UUID],
        category: ProjectMemoryCategory,
        user_id: uuid.UUID,
    ) -> ProjectMemory:
        sources: list[ProjectMemory] = []
        for sid in source_ids:
            result = await self.db.execute(
                select(ProjectMemory).where(
                    and_(
                        ProjectMemory.id == sid,
                        ProjectMemory.project_id == project_id,
                    )
                )
            )
            mem = result.scalar_one_or_none()
            if mem is not None:
                sources.append(mem)

        if not sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid source memories found for aggregation",
            )

        combined_content = "\n\n".join(
            f"[{s.category.value}] {s.content}" for s in sources
        )
        combined_metadata = {}
        source_memory_ids_str: list[str] = []
        for s in sources:
            source_memory_ids_str.append(str(s.id))
            if s.memory_metadata:
                combined_metadata.update(s.memory_metadata)

        aggregated = ProjectMemory(
            project_id=project_id,
            user_id=user_id,
            category=category,
            content=combined_content,
            importance=MemoryImportance.HIGH,
            confidence=min(
                (s.confidence for s in sources), default=1.0
            ),
            memory_metadata={
                "aggregated": True,
                "aggregated_at": datetime.now(timezone.utc).isoformat(),
                "source_count": len(sources),
                **combined_metadata,
            },
            source_memory_ids=source_memory_ids_str,
        )
        self.db.add(aggregated)
        await self.db.flush()
        logger.info(
            "aggregated project memories",
            extra={
                "aggregated_id": str(aggregated.id),
                "project_id": str(project_id),
                "source_count": len(sources),
                "category": category.value,
            },
        )
        if self._indexer is not None:
            await self._indexer.index_project_memory(aggregated)
        return aggregated

    async def get_by_project(
        self, project_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[ProjectMemory], int]:
        query = (
            select(ProjectMemory)
            .where(ProjectMemory.project_id == project_id)
            .order_by(ProjectMemory.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count(ProjectMemory.id)).where(
            ProjectMemory.project_id == project_id
        )

        result = await self.db.execute(query)
        memories = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        return memories, total

    async def search_by_category(
        self,
        project_id: uuid.UUID,
        category: ProjectMemoryCategory,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ProjectMemory], int]:
        query = (
            select(ProjectMemory)
            .where(
                and_(
                    ProjectMemory.project_id == project_id,
                    ProjectMemory.category == category,
                )
            )
            .order_by(ProjectMemory.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count(ProjectMemory.id)).where(
            and_(
                ProjectMemory.project_id == project_id,
                ProjectMemory.category == category,
            )
        )

        result = await self.db.execute(query)
        memories = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        return memories, total
