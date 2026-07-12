from __future__ import annotations

import uuid
from dataclasses import dataclass, field
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
from app.vectorstore.collections import CollectionName
from app.vectorstore.retrieval import similarity_search, RetrievalResult, RetrievedChunk

logger = get_logger("vectorstore.memory_search")
settings = get_settings()


@dataclass
class MemorySearchHit:
    memory_type: str
    memory_id: uuid.UUID
    user_id: uuid.UUID | None
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = "memory"


@dataclass
class MemorySearchResult:
    query: str
    results: list[MemorySearchHit]
    total: int
    per_collection: dict[str, int] = field(default_factory=dict)


_MEMORY_COLLECTIONS: list[CollectionName] = [
    CollectionName.MEMORY_SESSION,
    CollectionName.MEMORY_LONG_TERM,
    CollectionName.MEMORY_PAPER,
    CollectionName.MEMORY_PROJECT,
]

_MEMORY_TYPE_TO_CLASS = {
    "session_memory": SessionMemory,
    "long_term_memory": LongTermMemory,
    "paper_memory": PaperMemory,
    "project_memory": ProjectMemory,
}


class MemorySearch:
    """Semantic search over Research Memory vector collections.

    Searches one or more memory collections, resolves ChromaDB results
    back to full ORM model instances, and returns typed hit objects.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_all(
        self,
        query: str,
        user_id: uuid.UUID | None = None,
        top_k: int = 10,
        memory_types: list[str] | None = None,
    ) -> MemorySearchResult:
        collections = _MEMORY_COLLECTIONS
        if memory_types is not None:
            collections = [
                coll
                for mem_type, coll in [
                    ("session_memory", CollectionName.MEMORY_SESSION),
                    ("long_term_memory", CollectionName.MEMORY_LONG_TERM),
                    ("paper_memory", CollectionName.MEMORY_PAPER),
                    ("project_memory", CollectionName.MEMORY_PROJECT),
                ]
                if mem_type in memory_types
            ]

        all_hits: list[MemorySearchHit] = []
        per_collection: dict[str, int] = {}

        for coll in collections:
            try:
                filter_dict: dict[str, Any] | None = None
                if user_id is not None:
                    filter_dict = {"user_id": str(user_id)}

                result = await similarity_search(
                    collection=coll,
                    query=query,
                    top_k=top_k,
                    filter=filter_dict,
                )
                hits = await self._resolve_results(coll, result)
                all_hits.extend(hits)
                per_collection[coll.value] = len(hits)
            except Exception as exc:
                logger.warning(
                    "search failed for collection",
                    extra={"collection": coll.value, "error": str(exc)},
                )
                per_collection[coll.value] = 0

        all_hits.sort(key=lambda h: h.score, reverse=True)
        return MemorySearchResult(
            query=query,
            results=all_hits[:top_k],
            total=len(all_hits),
            per_collection=per_collection,
        )

    async def search_by_type(
        self,
        memory_type: str,
        query: str,
        user_id: uuid.UUID | None = None,
        top_k: int = 10,
    ) -> MemorySearchResult:
        collection_name = {
            "session_memory": CollectionName.MEMORY_SESSION,
            "long_term_memory": CollectionName.MEMORY_LONG_TERM,
            "paper_memory": CollectionName.MEMORY_PAPER,
            "project_memory": CollectionName.MEMORY_PROJECT,
        }.get(memory_type)

        if collection_name is None:
            logger.warning("unknown memory type", extra={"memory_type": memory_type})
            return MemorySearchResult(query=query, results=[], total=0)

        try:
            filter_dict: dict[str, Any] | None = None
            if user_id is not None:
                filter_dict = {"user_id": str(user_id)}

            result = await similarity_search(
                collection=collection_name,
                query=query,
                top_k=top_k,
                filter=filter_dict,
            )
            hits = await self._resolve_results(collection_name, result)
            return MemorySearchResult(
                query=query,
                results=hits,
                total=len(hits),
                per_collection={collection_name.value: len(hits)},
            )
        except Exception as exc:
            logger.error(
                "search by type failed",
                extra={"memory_type": memory_type, "error": str(exc)},
            )
            return MemorySearchResult(query=query, results=[], total=0)

    async def _resolve_results(
        self,
        collection: CollectionName,
        search_result: RetrievalResult,
    ) -> list[MemorySearchHit]:
        if not search_result.results:
            return []

        hits: list[MemorySearchHit] = []
        for chunk in search_result.results:
            mem_type = chunk.metadata.get("memory_type", "")
            mem_id_str = chunk.metadata.get("memory_id", "")
            if not mem_type or not mem_id_str:
                continue

            try:
                mem_id = uuid.UUID(mem_id_str)
            except ValueError:
                continue

            hits.append(
                MemorySearchHit(
                    memory_type=mem_type,
                    memory_id=mem_id,
                    user_id=_parse_uuid(chunk.metadata.get("user_id")),
                    content=chunk.content,
                    score=chunk.score,
                    metadata=chunk.metadata,
                )
            )

        return hits

    async def resolve_to_model(
        self, hit: MemorySearchHit
    ) -> SessionMemory | LongTermMemory | PaperMemory | ProjectMemory | None:
        model_cls = _MEMORY_TYPE_TO_CLASS.get(hit.memory_type)
        if model_cls is None:
            return None

        result = await self.db.execute(
            select(model_cls).where(model_cls.id == hit.memory_id)
        )
        return result.scalar_one_or_none()

    async def resolve_batch(
        self, hits: list[MemorySearchHit]
    ) -> list[SessionMemory | LongTermMemory | PaperMemory | ProjectMemory]:
        resolved: list[SessionMemory | LongTermMemory | PaperMemory | ProjectMemory] = []
        for hit in hits:
            model = await self.resolve_to_model(hit)
            if model is not None:
                resolved.append(model)
        return resolved


def _parse_uuid(val: Any) -> uuid.UUID | None:
    if val is None:
        return None
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError):
        return None
