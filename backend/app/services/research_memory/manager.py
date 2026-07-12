from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.research_memory import (
    SessionMemory,
    LongTermMemory,
    PaperMemory,
    ProjectMemory,
    UserResearchProfile,
    SemanticMemoryIndex,
    LongTermMemoryCategory,
    ProjectMemoryCategory,
)
from app.schemas.research_memory import (
    SessionMemoryCreate,
    SessionMemoryUpdate,
    LongTermMemoryCreate,
    LongTermMemoryUpdate,
    PaperMemoryCreate,
    ProjectMemoryCreate,
    ProjectMemoryUpdate,
    UserResearchProfileCreate,
    UserResearchProfileUpdate,
)
from app.services.research_memory.session_memory_service import SessionMemoryService
from app.services.research_memory.long_term_memory_service import LongTermMemoryService
from app.services.research_memory.paper_memory_service import PaperMemoryService
from app.services.research_memory.project_memory_service import ProjectMemoryService
from app.services.research_memory.user_profile_service import UserResearchProfileService
from app.services.research_memory.semantic_index_service import (
    SemanticMemoryIndexService,
)
from app.vectorstore.embeddings import EmbeddingProvider
from app.vectorstore.memory_indexer import MemoryIndexer
from app.vectorstore.memory_search import MemorySearch, MemorySearchResult

logger = get_logger("services.research_memory.manager")


class ResearchMemoryManager:
    """Unified orchestration layer for the Research Memory system.

    This is the single entry point for AI agents interacting with research
    memory.  It coordinates all existing services, the vector indexer,
    and semantic search without duplicating business logic.

    Usage::

        manager = ResearchMemoryManager(db=session, embedding_provider=...)
        memory = await manager.create_session_memory(data)
        results = await manager.search("deep learning papers")
    """

    def __init__(
        self,
        db: AsyncSession,
        embedding_provider: EmbeddingProvider | None = None,
        *,
        session_service: SessionMemoryService | None = None,
        long_term_service: LongTermMemoryService | None = None,
        paper_service: PaperMemoryService | None = None,
        project_service: ProjectMemoryService | None = None,
        profile_service: UserResearchProfileService | None = None,
        index_service: SemanticMemoryIndexService | None = None,
        indexer: MemoryIndexer | None = None,
        search: MemorySearch | None = None,
    ):
        # ------------------------------------------------------------------
        # Services – create with shared db and indexer for auto-indexing
        # ------------------------------------------------------------------
        self._indexer = indexer or MemoryIndexer(
            db=db, embedding_provider=embedding_provider
        )

        self._session_service = session_service or SessionMemoryService(
            db=db, indexer=self._indexer
        )
        self._long_term_service = long_term_service or LongTermMemoryService(
            db=db, indexer=self._indexer
        )
        self._paper_service = paper_service or PaperMemoryService(
            db=db, indexer=self._indexer
        )
        self._project_service = project_service or ProjectMemoryService(
            db=db, indexer=self._indexer
        )
        self._profile_service = profile_service or UserResearchProfileService(db=db)
        self._index_service = index_service or SemanticMemoryIndexService(db=db)
        self._search = search or MemorySearch(db=db)

    # ==================================================================
    # Session Memory
    # ==================================================================

    async def create_session_memory(self, data: SessionMemoryCreate) -> SessionMemory:
        return await self._session_service.create_memory(data)

    async def get_session_memory(self, memory_id: uuid.UUID) -> SessionMemory:
        return await self._session_service.get_memory(memory_id)

    async def update_session_memory(
        self, memory_id: uuid.UUID, data: SessionMemoryUpdate
    ) -> SessionMemory:
        return await self._session_service.update_memory(memory_id, data)

    async def delete_session_memory(self, memory_id: uuid.UUID) -> None:
        await self._session_service.delete_memory(memory_id)

    async def list_session_memories(
        self, session_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[SessionMemory], int]:
        return await self._session_service.get_by_session(session_id, skip, limit)

    async def list_session_memories_by_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[SessionMemory], int]:
        return await self._session_service.get_by_user(user_id, skip, limit)

    # ==================================================================
    # Long-Term Memory
    # ==================================================================

    async def store_long_term_memory(
        self, data: LongTermMemoryCreate
    ) -> LongTermMemory:
        return await self._long_term_service.store_memory(data)

    async def get_long_term_memory(self, memory_id: uuid.UUID) -> LongTermMemory:
        return await self._long_term_service.get_memory(memory_id)

    async def update_long_term_memory(
        self, memory_id: uuid.UUID, data: LongTermMemoryUpdate
    ) -> LongTermMemory:
        return await self._long_term_service.update_memory(memory_id, data)

    async def delete_long_term_memory(self, memory_id: uuid.UUID) -> None:
        await self._long_term_service.delete_memory(memory_id)

    async def archive_long_term_memory(self, memory_id: uuid.UUID) -> LongTermMemory:
        return await self._long_term_service.archive_memory(memory_id)

    async def merge_long_term_memories(
        self, memory_ids: list[uuid.UUID]
    ) -> LongTermMemory:
        return await self._long_term_service.merge_duplicates(memory_ids)

    async def list_long_term_memories(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[LongTermMemory], int]:
        return await self._long_term_service.get_by_user(user_id, skip, limit)

    async def search_long_term_by_category(
        self,
        user_id: uuid.UUID,
        category: LongTermMemoryCategory,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[LongTermMemory], int]:
        return await self._long_term_service.search_by_category(
            user_id, category, skip, limit
        )

    # ==================================================================
    # Paper Memory
    # ==================================================================

    async def store_paper_memory(self, data: PaperMemoryCreate) -> PaperMemory:
        return await self._paper_service.store_memory(data)

    async def get_paper_memory(self, memory_id: uuid.UUID) -> PaperMemory:
        return await self._paper_service.get_memory(memory_id)

    async def delete_paper_memory(self, memory_id: uuid.UUID) -> None:
        await self._paper_service.delete_memory(memory_id)

    async def list_paper_memories(
        self, project_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[PaperMemory], int]:
        return await self._paper_service.get_by_project(project_id, skip, limit)

    async def list_paper_memories_by_doi(
        self, doi: str, skip: int = 0, limit: int = 50
    ) -> tuple[list[PaperMemory], int]:
        return await self._paper_service.get_by_doi(doi, skip, limit)

    # ==================================================================
    # Project Memory
    # ==================================================================

    async def create_project_memory(self, data: ProjectMemoryCreate) -> ProjectMemory:
        return await self._project_service.create_memory(data)

    async def get_project_memory(self, memory_id: uuid.UUID) -> ProjectMemory:
        return await self._project_service.get_memory(memory_id)

    async def update_project_memory(
        self, memory_id: uuid.UUID, data: ProjectMemoryUpdate
    ) -> ProjectMemory:
        return await self._project_service.update_memory(memory_id, data)

    async def delete_project_memory(self, memory_id: uuid.UUID) -> None:
        await self._project_service.delete_memory(memory_id)

    async def list_project_memories(
        self, project_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[ProjectMemory], int]:
        return await self._project_service.get_by_project(project_id, skip, limit)

    async def aggregate_project_memories(
        self,
        project_id: uuid.UUID,
        source_ids: list[uuid.UUID],
        category: ProjectMemoryCategory,
        user_id: uuid.UUID,
    ) -> ProjectMemory:
        return await self._project_service.aggregate_memories(
            project_id, source_ids, category, user_id
        )

    async def search_project_memories_by_category(
        self,
        project_id: uuid.UUID,
        category: ProjectMemoryCategory,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ProjectMemory], int]:
        return await self._project_service.search_by_category(
            project_id, category, skip, limit
        )

    # ==================================================================
    # User Research Profile
    # ==================================================================

    async def create_profile(
        self, user_id: uuid.UUID, data: UserResearchProfileCreate
    ) -> UserResearchProfile:
        return await self._profile_service.create_profile(user_id, data)

    async def get_profile(self, user_id: uuid.UUID) -> UserResearchProfile:
        return await self._profile_service.get_profile(user_id)

    async def update_profile(
        self, user_id: uuid.UUID, data: UserResearchProfileUpdate
    ) -> UserResearchProfile:
        return await self._profile_service.update_profile(user_id, data)

    async def delete_profile(self, user_id: uuid.UUID) -> None:
        await self._profile_service.delete_profile(user_id)

    async def update_profile_expertise(
        self, user_id: uuid.UUID, expertise_areas: list[str]
    ) -> UserResearchProfile:
        return await self._profile_service.update_expertise(user_id, expertise_areas)

    async def update_profile_interests(
        self, user_id: uuid.UUID, research_interests: list[str]
    ) -> UserResearchProfile:
        return await self._profile_service.update_interests(user_id, research_interests)

    async def update_profile_preferences(
        self, user_id: uuid.UUID, preferences: dict[str, Any]
    ) -> UserResearchProfile:
        return await self._profile_service.update_preferences(user_id, preferences)

    # ==================================================================
    # Semantic Search
    # ==================================================================

    async def search(
        self,
        query: str,
        user_id: uuid.UUID | None = None,
        top_k: int = 10,
        memory_types: list[str] | None = None,
    ) -> MemorySearchResult:
        return await self._search.search_all(
            query=query,
            user_id=user_id,
            top_k=top_k,
            memory_types=memory_types,
        )

    async def search_by_type(
        self,
        memory_type: str,
        query: str,
        user_id: uuid.UUID | None = None,
        top_k: int = 10,
    ) -> MemorySearchResult:
        return await self._search.search_by_type(
            memory_type=memory_type,
            query=query,
            user_id=user_id,
            top_k=top_k,
        )

    async def search_keyword(
        self,
        query: str,
        user_id: uuid.UUID | None = None,
        memory_types: list[str] | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[SessionMemory | LongTermMemory | PaperMemory | ProjectMemory]:
        """Keyword (non-semantic) search via database text matching.

        This is a simple LIKE-based fallback for cases where vector search
        is unavailable or a literal match is preferred.
        """
        from sqlalchemy import or_, select

        results: list[SessionMemory | LongTermMemory | PaperMemory | ProjectMemory] = []
        pattern = f"%{query}%"

        targets = memory_types or [
            "session_memory",
            "long_term_memory",
            "paper_memory",
            "project_memory",
        ]

        for mem_type in targets:
            try:
                if mem_type == "session_memory":
                    stmt = (
                        select(SessionMemory)
                        .where(SessionMemory.content.ilike(pattern))
                        .offset(skip)
                        .limit(limit)
                    )
                    if user_id:
                        stmt = stmt.where(SessionMemory.user_id == user_id)
                    result = await self._session_service.db.execute(stmt)
                    results.extend(result.scalars().all())

                elif mem_type == "long_term_memory":
                    stmt = (
                        select(LongTermMemory)
                        .where(LongTermMemory.content.ilike(pattern))
                        .offset(skip)
                        .limit(limit)
                    )
                    if user_id:
                        stmt = stmt.where(LongTermMemory.user_id == user_id)
                    result = await self._long_term_service.db.execute(stmt)
                    results.extend(result.scalars().all())

                elif mem_type == "paper_memory":
                    stmt = (
                        select(PaperMemory)
                        .where(
                            or_(
                                PaperMemory.content.ilike(pattern),
                                PaperMemory.summary.ilike(pattern),
                                PaperMemory.source_paper_title.ilike(pattern),
                            )
                        )
                        .offset(skip)
                        .limit(limit)
                    )
                    if user_id:
                        stmt = stmt.where(PaperMemory.user_id == user_id)
                    result = await self._paper_service.db.execute(stmt)
                    results.extend(result.scalars().all())

                elif mem_type == "project_memory":
                    stmt = (
                        select(ProjectMemory)
                        .where(
                            or_(
                                ProjectMemory.content.ilike(pattern),
                                ProjectMemory.summary.ilike(pattern),
                            )
                        )
                        .offset(skip)
                        .limit(limit)
                    )
                    if user_id:
                        stmt = stmt.where(ProjectMemory.user_id == user_id)
                    result = await self._project_service.db.execute(stmt)
                    results.extend(result.scalars().all())

            except Exception as exc:
                logger.warning(
                    "keyword search failed",
                    extra={"memory_type": mem_type, "error": str(exc)},
                )

        return results

    async def search_hybrid(
        self,
        query: str,
        user_id: uuid.UUID | None = None,
        top_k: int = 10,
        memory_types: list[str] | None = None,
        semantic_weight: float = 0.7,
    ) -> MemorySearchResult:
        """Hybrid search combining semantic (vector) and keyword scores.

        Placeholder: currently returns only semantic results.
        Future: merge and re-rank results from both search methods using
        ``semantic_weight`` for the semantic portion and ``1 - semantic_weight``
        for the keyword portion.
        """
        return await self._search.search_all(
            query=query,
            user_id=user_id,
            top_k=top_k,
            memory_types=memory_types,
        )

    # ==================================================================
    # Indexing Operations
    # ==================================================================

    async def ensure_collections(self) -> list[str]:
        return await self._indexer.ensure_collections()

    async def reindex_memory(
        self, memory_type: str, memory_id: uuid.UUID
    ) -> SemanticMemoryIndex | None:
        return await self._indexer.reindex_memory(memory_type, memory_id)

    async def index_all(
        self,
        memory_types: list[str] | None = None,
        batch_size: int = 100,
    ) -> dict[str, int]:
        """Index all existing memory entries (bulk backfill).

        Returns counts per memory type: ``{"session_memory": 5, ...}``
        """
        from sqlalchemy import select

        counts: dict[str, int] = {}
        targets = memory_types or [
            "session_memory",
            "long_term_memory",
            "paper_memory",
            "project_memory",
        ]

        for mem_type in targets:
            count = 0
            try:
                if mem_type == "session_memory":
                    result = await self._session_service.db.execute(
                        select(SessionMemory)
                    )
                    for mem in result.scalars().all():
                        await self._indexer.index_session_memory(mem)
                        count += 1

                elif mem_type == "long_term_memory":
                    result = await self._long_term_service.db.execute(
                        select(LongTermMemory)
                    )
                    for mem in result.scalars().all():
                        await self._indexer.index_long_term_memory(mem)
                        count += 1

                elif mem_type == "paper_memory":
                    result = await self._paper_service.db.execute(select(PaperMemory))
                    for mem in result.scalars().all():
                        await self._indexer.index_paper_memory(mem)
                        count += 1

                elif mem_type == "project_memory":
                    result = await self._project_service.db.execute(
                        select(ProjectMemory)
                    )
                    for mem in result.scalars().all():
                        await self._indexer.index_project_memory(mem)
                        count += 1

                counts[mem_type] = count
                logger.info(
                    "bulk indexed memory type",
                    extra={"memory_type": mem_type, "count": count},
                )
            except Exception as exc:
                logger.error(
                    "bulk indexing failed",
                    extra={"memory_type": mem_type, "error": str(exc)},
                )
                counts[mem_type] = -1

        return counts

    # ==================================================================
    # Component accessors – for future AI agent integration
    # ==================================================================

    @property
    def session_service(self) -> SessionMemoryService:
        return self._session_service

    @property
    def long_term_service(self) -> LongTermMemoryService:
        return self._long_term_service

    @property
    def paper_service(self) -> PaperMemoryService:
        return self._paper_service

    @property
    def project_service(self) -> ProjectMemoryService:
        return self._project_service

    @property
    def profile_service(self) -> UserResearchProfileService:
        return self._profile_service

    @property
    def index_service(self) -> SemanticMemoryIndexService:
        return self._index_service

    @property
    def indexer(self) -> MemoryIndexer:
        return self._indexer

    @property
    def search_engine(self) -> MemorySearch:
        return self._search
