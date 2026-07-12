from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.research_memory import PaperMemory
from app.schemas.research_memory import PaperMemoryCreate
from app.vectorstore.memory_indexer import MemoryIndexer

logger = get_logger("services.research_memory.paper_memory")


class PaperMemoryService:
    def __init__(self, db: AsyncSession, indexer: MemoryIndexer | None = None):
        self.db = db
        self._indexer = indexer

    async def get_memory(self, memory_id: uuid.UUID) -> PaperMemory:
        result = await self.db.execute(
            select(PaperMemory).where(PaperMemory.id == memory_id)
        )
        memory = result.scalar_one_or_none()
        if memory is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paper memory not found",
            )
        return memory

    async def store_memory(self, data: PaperMemoryCreate) -> PaperMemory:
        memory = PaperMemory(
            project_id=data.project_id,
            document_id=data.document_id,
            user_id=data.user_id,
            memory_type=data.memory_type,
            content=data.content,
            summary=data.summary,
            source_paper_title=data.source_paper_title,
            source_doi=data.source_doi,
            relevance_score=data.relevance_score,
            memory_metadata=data.memory_metadata,
        )
        self.db.add(memory)
        await self.db.flush()
        logger.info(
            "stored paper memory",
            extra={
                "memory_id": str(memory.id),
                "project_id": str(data.project_id),
                "memory_type": data.memory_type.value,
            },
        )
        if self._indexer is not None:
            await self._indexer.index_paper_memory(memory)
        return memory

    async def delete_memory(self, memory_id: uuid.UUID) -> None:
        memory = await self.get_memory(memory_id)
        await self.db.delete(memory)
        await self.db.flush()
        logger.info("deleted paper memory", extra={"memory_id": str(memory_id)})
        if self._indexer is not None:
            await self._indexer.remove_paper_memory(memory_id)

    async def get_by_project(
        self, project_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[PaperMemory], int]:
        query = (
            select(PaperMemory)
            .where(PaperMemory.project_id == project_id)
            .order_by(PaperMemory.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count(PaperMemory.id)).where(
            PaperMemory.project_id == project_id
        )

        result = await self.db.execute(query)
        memories = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        return memories, total

    async def get_by_document(
        self, document_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[PaperMemory], int]:
        query = (
            select(PaperMemory)
            .where(PaperMemory.document_id == document_id)
            .order_by(PaperMemory.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count(PaperMemory.id)).where(
            PaperMemory.document_id == document_id
        )

        result = await self.db.execute(query)
        memories = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        return memories, total

    async def get_by_doi(
        self, doi: str, skip: int = 0, limit: int = 50
    ) -> tuple[list[PaperMemory], int]:
        query = (
            select(PaperMemory)
            .where(PaperMemory.source_doi == doi)
            .order_by(PaperMemory.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count(PaperMemory.id)).where(
            PaperMemory.source_doi == doi
        )

        result = await self.db.execute(query)
        memories = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        return memories, total

    async def search_by_relevance(
        self,
        project_id: uuid.UUID,
        min_score: float = 0.0,
        max_score: float = 1.0,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[PaperMemory], int]:
        query = (
            select(PaperMemory)
            .where(
                and_(
                    PaperMemory.project_id == project_id,
                    PaperMemory.relevance_score >= min_score,
                    PaperMemory.relevance_score <= max_score,
                )
            )
            .order_by(PaperMemory.relevance_score.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count(PaperMemory.id)).where(
            and_(
                PaperMemory.project_id == project_id,
                PaperMemory.relevance_score >= min_score,
                PaperMemory.relevance_score <= max_score,
            )
        )

        result = await self.db.execute(query)
        memories = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        return memories, total
