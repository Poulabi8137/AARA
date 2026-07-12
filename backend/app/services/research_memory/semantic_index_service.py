from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.research_memory import SemanticMemoryIndex
from app.schemas.research_memory import (
    SemanticMemoryIndexCreate,
    SemanticMemoryIndexUpdate,
)

logger = get_logger("services.research_memory.semantic_index")


class SemanticMemoryIndexService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_index(self, index_id: uuid.UUID) -> SemanticMemoryIndex:
        result = await self.db.execute(
            select(SemanticMemoryIndex).where(SemanticMemoryIndex.id == index_id)
        )
        index = result.scalar_one_or_none()
        if index is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Semantic memory index not found",
            )
        return index

    async def register_embedding(
        self, data: SemanticMemoryIndexCreate
    ) -> SemanticMemoryIndex:
        existing = await self.db.execute(
            select(SemanticMemoryIndex).where(
                and_(
                    SemanticMemoryIndex.memory_type == data.memory_type,
                    SemanticMemoryIndex.memory_id == data.memory_id,
                    SemanticMemoryIndex.embedding_id == data.embedding_id,
                )
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Embedding already registered for this memory",
            )

        index = SemanticMemoryIndex(
            memory_type=data.memory_type,
            memory_id=data.memory_id,
            user_id=data.user_id,
            embedding_id=data.embedding_id,
            collection_name=data.collection_name,
            content_hash=data.content_hash,
            chunk_index=data.chunk_index,
            memory_metadata=data.memory_metadata,
        )
        self.db.add(index)
        await self.db.flush()
        logger.info(
            "registered embedding",
            extra={
                "index_id": str(index.id),
                "memory_type": data.memory_type,
                "embedding_id": data.embedding_id,
            },
        )
        return index

    async def update_embedding(
        self, index_id: uuid.UUID, data: SemanticMemoryIndexUpdate
    ) -> SemanticMemoryIndex:
        index = await self.get_index(index_id)

        if data.embedding_id is not None:
            index.embedding_id = data.embedding_id
        if data.collection_name is not None:
            index.collection_name = data.collection_name
        if data.memory_metadata is not None:
            index.memory_metadata = data.memory_metadata

        await self.db.flush()
        return index

    async def delete_embedding(self, index_id: uuid.UUID) -> None:
        index = await self.get_index(index_id)
        await self.db.delete(index)
        await self.db.flush()
        logger.info("deleted embedding", extra={"index_id": str(index_id)})

    async def delete_by_embedding_id(self, embedding_id: str) -> None:
        result = await self.db.execute(
            select(SemanticMemoryIndex).where(
                SemanticMemoryIndex.embedding_id == embedding_id
            )
        )
        indices = list(result.scalars().all())
        for index in indices:
            await self.db.delete(index)
        await self.db.flush()
        if indices:
            logger.info(
                "deleted embeddings by id",
                extra={"embedding_id": embedding_id, "count": len(indices)},
            )

    async def lookup_by_embedding_id(
        self, embedding_id: str
    ) -> SemanticMemoryIndex | None:
        result = await self.db.execute(
            select(SemanticMemoryIndex).where(
                SemanticMemoryIndex.embedding_id == embedding_id
            )
        )
        return result.scalar_one_or_none()

    async def lookup_by_memory(
        self, memory_type: str, memory_id: uuid.UUID
    ) -> list[SemanticMemoryIndex]:
        result = await self.db.execute(
            select(SemanticMemoryIndex)
            .where(
                and_(
                    SemanticMemoryIndex.memory_type == memory_type,
                    SemanticMemoryIndex.memory_id == memory_id,
                )
            )
            .order_by(SemanticMemoryIndex.chunk_index.asc().nullslast())
        )
        return list(result.scalars().all())

    async def validate_content_hash(self, content_hash: str) -> bool:
        result = await self.db.execute(
            select(func.count(SemanticMemoryIndex.id)).where(
                SemanticMemoryIndex.content_hash == content_hash
            )
        )
        count = result.scalar_one()
        return count == 0

    async def list_by_collection(
        self, collection_name: str, skip: int = 0, limit: int = 50
    ) -> tuple[list[SemanticMemoryIndex], int]:
        query = (
            select(SemanticMemoryIndex)
            .where(SemanticMemoryIndex.collection_name == collection_name)
            .order_by(SemanticMemoryIndex.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count(SemanticMemoryIndex.id)).where(
            SemanticMemoryIndex.collection_name == collection_name
        )

        result = await self.db.execute(query)
        indices = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        return indices, total
