from __future__ import annotations

import hashlib
import uuid
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.research_memory import (
    SessionMemory,
    LongTermMemory,
    PaperMemory,
    ProjectMemory,
    SemanticMemoryIndex,
)
from app.vectorstore.collections import CollectionName, get_collection
from app.vectorstore.embeddings import EmbeddingProvider
from app.vectorstore.provider_factory import get_embedding_provider
from app.vectorstore.retrieval import (
    add_document,
    delete_documents_by_filter,
)

logger = get_logger("vectorstore.memory_indexer")
settings = get_settings()


_MEMORY_TYPE_COLLECTION_MAP: dict[str, CollectionName] = {
    "session_memory": CollectionName.MEMORY_SESSION,
    "long_term_memory": CollectionName.MEMORY_LONG_TERM,
    "paper_memory": CollectionName.MEMORY_PAPER,
    "project_memory": CollectionName.MEMORY_PROJECT,
}

_MEMORY_COLLECTION_TYPE_MAP: dict[CollectionName, str] = {
    CollectionName.MEMORY_SESSION: "session_memory",
    CollectionName.MEMORY_LONG_TERM: "long_term_memory",
    CollectionName.MEMORY_PAPER: "paper_memory",
    CollectionName.MEMORY_PROJECT: "project_memory",
}


def _content_hash(content: str, prefix: str = "") -> str:
    raw = f"{prefix}:{content}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:64]


def _build_metadata(
    memory_type: str,
    memory_id: uuid.UUID,
    user_id: uuid.UUID | None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "memory_type": memory_type,
        "memory_id": str(memory_id),
    }
    if user_id is not None:
        meta["user_id"] = str(user_id)
    if extra:
        meta.update(extra)
    return meta


class MemoryIndexer:
    """Indexes, updates, and removes Research Memory entries in ChromaDB.

    Each memory type (session, long-term, paper, project) maps to a dedicated
    ChromaDB collection.  Content hashes are used to skip re-embedding when
    identical content already exists in the same collection.
    """

    def __init__(
        self,
        db: AsyncSession,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self.db = db
        self._embedding_provider = embedding_provider or get_embedding_provider()

    # ------------------------------------------------------------------
    # Session Memory
    # ------------------------------------------------------------------

    async def index_session_memory(
        self, memory: SessionMemory
    ) -> SemanticMemoryIndex | None:
        return await self._index_memory(
            memory_type="session_memory",
            memory_id=memory.id,
            user_id=memory.user_id,
            content=memory.content,
            embedding_id=f"session_{memory.id}",
            extra_metadata={
                "session_id": str(memory.session_id),
                "memory_type_enum": memory.memory_type.value,
                "importance": memory.importance.value,
                "source": memory.source.value,
                "confidence": memory.confidence,
            },
        )

    async def remove_session_memory(self, memory_id: uuid.UUID) -> None:
        await self._remove_memory("session_memory", memory_id)

    # ------------------------------------------------------------------
    # Long-Term Memory
    # ------------------------------------------------------------------

    async def index_long_term_memory(
        self, memory: LongTermMemory
    ) -> SemanticMemoryIndex | None:
        return await self._index_memory(
            memory_type="long_term_memory",
            memory_id=memory.id,
            user_id=memory.user_id,
            content=memory.content,
            embedding_id=f"ltm_{memory.id}",
            extra_metadata={
                "category": memory.category.value,
                "importance": memory.importance.value,
                "confidence": memory.confidence,
            },
        )

    async def remove_long_term_memory(self, memory_id: uuid.UUID) -> None:
        await self._remove_memory("long_term_memory", memory_id)

    # ------------------------------------------------------------------
    # Paper Memory
    # ------------------------------------------------------------------

    async def index_paper_memory(
        self, memory: PaperMemory
    ) -> SemanticMemoryIndex | None:
        return await self._index_memory(
            memory_type="paper_memory",
            memory_id=memory.id,
            user_id=memory.user_id,
            content=memory.content,
            embedding_id=f"pm_{memory.id}",
            extra_metadata={
                "project_id": str(memory.project_id),
                "memory_type_enum": memory.memory_type.value,
                "relevance_score": memory.relevance_score,
            },
        )

    async def remove_paper_memory(self, memory_id: uuid.UUID) -> None:
        await self._remove_memory("paper_memory", memory_id)

    # ------------------------------------------------------------------
    # Project Memory
    # ------------------------------------------------------------------

    async def index_project_memory(
        self, memory: ProjectMemory
    ) -> SemanticMemoryIndex | None:
        return await self._index_memory(
            memory_type="project_memory",
            memory_id=memory.id,
            user_id=memory.user_id,
            content=memory.content,
            embedding_id=f"projmem_{memory.id}",
            extra_metadata={
                "project_id": str(memory.project_id),
                "category": memory.category.value,
                "importance": memory.importance.value,
                "confidence": memory.confidence,
            },
        )

    async def remove_project_memory(self, memory_id: uuid.UUID) -> None:
        await self._remove_memory("project_memory", memory_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _index_memory(
        self,
        memory_type: str,
        memory_id: uuid.UUID,
        user_id: uuid.UUID | None,
        content: str,
        embedding_id: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> SemanticMemoryIndex | None:
        if not settings.memory_indexing_enabled:
            return None

        collection = _MEMORY_TYPE_COLLECTION_MAP.get(memory_type)
        if collection is None:
            logger.warning("unknown memory type", extra={"memory_type": memory_type})
            return None

        meta = _build_metadata(memory_type, memory_id, user_id, extra_metadata)
        ch = _content_hash(content, prefix=memory_type)

        # Dedup: if content_hash already exists, skip embedding
        existing = await self.db.execute(
            select(SemanticMemoryIndex).where(
                and_(
                    SemanticMemoryIndex.memory_type == memory_type,
                    SemanticMemoryIndex.content_hash == ch,
                )
            )
        )
        existing_idx = existing.scalar_one_or_none()

        if existing_idx is not None:
            logger.debug(
                "content hash collision — skipping embedding",
                extra={
                    "memory_type": memory_type,
                    "memory_id": str(memory_id),
                    "content_hash": ch,
                    "existing_index_id": str(existing_idx.id),
                },
            )
            return existing_idx

        mem_id_str = str(memory_id)

        # Remove old index entries for this memory (if re-indexing)
        await self._remove_index_entries(memory_type, memory_id)

        # Add to ChromaDB
        await get_collection(collection)
        await add_document(
            collection=collection,
            doc_id=embedding_id,
            content=content,
            metadata=meta,
        )

        # Persist SemanticMemoryIndex record
        index_record = SemanticMemoryIndex(
            memory_type=memory_type,
            memory_id=memory_id,
            user_id=user_id,
            embedding_id=embedding_id,
            collection_name=collection.value,
            content_hash=ch,
            memory_metadata=meta,
        )
        self.db.add(index_record)
        await self.db.flush()

        logger.info(
            "indexed memory in vector store",
            extra={
                "memory_type": memory_type,
                "memory_id": mem_id_str,
                "embedding_id": embedding_id,
                "collection": collection.value,
            },
        )
        return index_record

    async def _remove_memory(self, memory_type: str, memory_id: uuid.UUID) -> None:
        collection = _MEMORY_TYPE_COLLECTION_MAP.get(memory_type)
        if collection is None:
            return

        # Remove from ChromaDB
        await delete_documents_by_filter(
            collection=collection,
            filter={"memory_id": str(memory_id)},
        )

        # Remove SemanticMemoryIndex records
        await self._remove_index_entries(memory_type, memory_id)
        await self.db.flush()

        logger.info(
            "removed memory from vector store",
            extra={
                "memory_type": memory_type,
                "memory_id": str(memory_id),
            },
        )

    async def _remove_index_entries(
        self, memory_type: str, memory_id: uuid.UUID
    ) -> None:
        result = await self.db.execute(
            select(SemanticMemoryIndex).where(
                and_(
                    SemanticMemoryIndex.memory_type == memory_type,
                    SemanticMemoryIndex.memory_id == memory_id,
                )
            )
        )
        for entry in result.scalars().all():
            await self.db.delete(entry)

    async def ensure_collections(self) -> list[str]:
        created: list[str] = []
        for coll in _MEMORY_TYPE_COLLECTION_MAP.values():
            await get_collection(coll)
            created.append(coll.value)
        logger.info("ensured memory collections exist", extra={"collections": created})
        return created

    async def reindex_memory(
        self, memory_type: str, memory_id: uuid.UUID
    ) -> SemanticMemoryIndex | None:
        if memory_type == "session_memory":
            result = await self.db.execute(
                select(SessionMemory).where(SessionMemory.id == memory_id)
            )
            memory = result.scalar_one_or_none()
            return await self.index_session_memory(memory) if memory else None

        if memory_type == "long_term_memory":
            result = await self.db.execute(
                select(LongTermMemory).where(LongTermMemory.id == memory_id)
            )
            memory = result.scalar_one_or_none()
            return await self.index_long_term_memory(memory) if memory else None

        if memory_type == "paper_memory":
            result = await self.db.execute(
                select(PaperMemory).where(PaperMemory.id == memory_id)
            )
            memory = result.scalar_one_or_none()
            return await self.index_paper_memory(memory) if memory else None

        if memory_type == "project_memory":
            result = await self.db.execute(
                select(ProjectMemory).where(ProjectMemory.id == memory_id)
            )
            memory = result.scalar_one_or_none()
            return await self.index_project_memory(memory) if memory else None

        logger.warning(
            "unknown memory type for reindex", extra={"memory_type": memory_type}
        )
        return None
