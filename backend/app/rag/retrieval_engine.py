from __future__ import annotations

import time
from typing import Any

from app.core.logging import get_logger
from app.rag.collection_router import CollectionRouter
from app.rag.config import get_rag_settings
from app.rag.models import (
    CollectionAnalytics,
    ProcessedQuery,
    RetrievedEvidence,
    RetrievalStrategy,
    SourceType,
)
from app.services.research_memory.manager import ResearchMemoryManager
from app.vectorstore.collections import CollectionName

logger = get_logger("rag.retrieval_engine")
settings = get_rag_settings()

_PLATFORM_COLLECTION_MAP: dict[SourceType, CollectionName] = {
    SourceType.CHROMA_PAPER: CollectionName.RESEARCH_PAPERS,
    SourceType.CHROMA_WEB: CollectionName.WEB_SEARCH_RESULTS,
    SourceType.CHROMA_CITATION: CollectionName.CITATIONS,
    SourceType.CHROMA_REPORT: CollectionName.GENERATED_REPORTS,
    SourceType.CHROMA_KNOWLEDGE: CollectionName.KNOWLEDGE_BASE,
}

_MEMORY_SOURCE_TYPES = frozenset({
    SourceType.MEMORY_SESSION,
    SourceType.MEMORY_LONG_TERM,
    SourceType.MEMORY_PAPER,
    SourceType.MEMORY_PROJECT,
})


class RetrievalEngine:
    def __init__(
        self,
        memory_manager: ResearchMemoryManager,
        vectorstore: Any,
        collection_router: CollectionRouter | None = None,
    ):
        self._memory = memory_manager
        self._vectorstore = vectorstore
        self._router = collection_router or CollectionRouter()

    async def retrieve_semantic(
        self,
        query: ProcessedQuery,
        top_k: int | None = None,
    ) -> list[RetrievedEvidence]:
        k = top_k or query.top_k or settings.retrieval_semantic_top_k
        result = await self._memory.search(
            query=query.rewritten or query.normalized,
            user_id=query.user_id,
            top_k=k,
            memory_types=None,
        )
        evidence = []
        for hit in result.results:
            src_type = (
                SourceType(hit.memory_type)
                if hit.memory_type in SourceType._value2member_map_
                else SourceType.MEMORY_SESSION
            )
            evidence.append(
                RetrievedEvidence(
                    content=hit.content,
                    source_type=src_type,
                    source_id=str(hit.memory_id),
                    score=hit.score,
                    metadata=hit.metadata,
                )
            )
        logger.info(
            "semantic retrieval complete (memory)",
            extra={"query": query.normalized[:80], "hits": len(evidence), "top_k": k},
        )
        return evidence

    async def retrieve_keyword(
        self,
        query: ProcessedQuery,
        top_k: int | None = None,
    ) -> list[RetrievedEvidence]:
        k = top_k or query.top_k or settings.retrieval_keyword_top_k
        models = await self._memory.search_keyword(
            query=query.rewritten or query.normalized,
            user_id=query.user_id,
            limit=k,
        )
        evidence = []
        for model in models:
            mem_type = type(model).__name__
            src_map = {
                "SessionMemory": SourceType.MEMORY_SESSION,
                "LongTermMemory": SourceType.MEMORY_LONG_TERM,
                "PaperMemory": SourceType.MEMORY_PAPER,
                "ProjectMemory": SourceType.MEMORY_PROJECT,
            }
            src_type = src_map.get(mem_type, SourceType.MEMORY_SESSION)
            evidence.append(
                RetrievedEvidence(
                    content=getattr(model, "content", ""),
                    source_type=src_type,
                    source_id=str(getattr(model, "id", "")),
                    score=0.5,
                    metadata=getattr(model, "memory_metadata", {}) or {},
                )
            )
        logger.info(
            "keyword retrieval complete (memory)",
            extra={"query": query.normalized[:80], "hits": len(evidence)},
        )
        return evidence

    async def retrieve_hybrid(
        self,
        query: ProcessedQuery,
        semantic_top_k: int | None = None,
        keyword_top_k: int | None = None,
    ) -> list[RetrievedEvidence]:
        semantic_k = semantic_top_k or settings.retrieval_semantic_top_k
        keyword_k = keyword_top_k or settings.retrieval_keyword_top_k
        semantic_results = await self.retrieve_semantic(query, top_k=semantic_k)
        keyword_results = await self.retrieve_keyword(query, top_k=keyword_k)
        seen_ids: set[str] = set()
        merged: list[RetrievedEvidence] = []
        weight = settings.retrieval_hybrid_weight
        for ev in semantic_results:
            ev.score *= weight
            merged.append(ev)
            seen_ids.add(ev.source_id)
        for ev in keyword_results:
            if ev.source_id not in seen_ids:
                ev.score *= 1.0 - weight
                merged.append(ev)
        merged.sort(key=lambda e: e.score, reverse=True)
        logger.info(
            "hybrid retrieval complete (memory)",
            extra={
                "query": query.normalized[:80],
                "semantic": len(semantic_results),
                "keyword": len(keyword_results),
                "merged": len(merged),
            },
        )
        return merged

    async def retrieve_platform(
        self,
        query: ProcessedQuery,
        source_types: list[SourceType],
        top_k: int | None = None,
    ) -> tuple[list[RetrievedEvidence], list[CollectionAnalytics]]:
        k = top_k or settings.retrieval_platform_top_k
        results: list[RetrievedEvidence] = []
        analytics: list[CollectionAnalytics] = []

        for src_type in source_types:
            coll_name = _PLATFORM_COLLECTION_MAP.get(src_type)
            if not coll_name:
                continue

            start = time.monotonic()
            try:
                collection = await self._vectorstore.get_collection(coll_name.value)
                hits = collection.similarity_search_with_relevance_scores(
                    query=query.rewritten or query.normalized,
                    k=k,
                )
            except Exception as exc:
                logger.warning(
                    "platform collection search failed",
                    extra={"collection": coll_name.value, "error": str(exc)},
                )
                analytics.append(
                    CollectionAnalytics(
                        collection=src_type,
                        hits=0,
                        latency_ms=0.0,
                        search_strategy="failed",
                    )
                )
                continue

            latency = (time.monotonic() - start) * 1000
            collection_hits = 0
            for doc, score in hits:
                collection_hits += 1
                results.append(
                    RetrievedEvidence(
                        content=doc.page_content,
                        source_type=src_type,
                        source_id=doc.metadata.get("id", "") or doc.id or str(hash(doc.page_content[:100])),
                        score=score,
                        metadata=doc.metadata,
                        provenance=f"chroma:{coll_name.value}",
                    )
                )

            analytics.append(
                CollectionAnalytics(
                    collection=src_type,
                    hits=collection_hits,
                    latency_ms=round(latency, 1),
                    search_strategy="semantic",
                )
            )

            logger.info(
                "platform collection search complete",
                extra={
                    "collection": coll_name.value,
                    "hits": collection_hits,
                    "latency_ms": round(latency, 1),
                },
            )

        return results, analytics

    async def retrieve(
        self,
        query: ProcessedQuery,
        route_collections: list[SourceType] | None = None,
    ) -> tuple[list[RetrievedEvidence], list[CollectionAnalytics]]:
        all_evidence: list[RetrievedEvidence] = []
        all_analytics: list[CollectionAnalytics] = []

        if route_collections:
            memory_types = [c for c in route_collections if c in _MEMORY_SOURCE_TYPES]
            platform_types = [c for c in route_collections if c not in _MEMORY_SOURCE_TYPES]
        else:
            memory_types = list(_MEMORY_SOURCE_TYPES)
            platform_types = list(_PLATFORM_COLLECTION_MAP.keys())

        if memory_types:
            if RetrievalStrategy.HYBRID in query.search_strategies:
                all_evidence.extend(await self.retrieve_hybrid(query))
            else:
                for strategy in query.search_strategies:
                    if strategy == RetrievalStrategy.SEMANTIC:
                        all_evidence.extend(await self.retrieve_semantic(query))
                    elif strategy == RetrievalStrategy.KEYWORD:
                        all_evidence.extend(await self.retrieve_keyword(query))

        if platform_types:
            platform_hits, platform_analytics = await self.retrieve_platform(query, platform_types)
            all_evidence.extend(platform_hits)
            all_analytics.extend(platform_analytics)

        all_evidence.sort(key=lambda e: e.score, reverse=True)
        return all_evidence, all_analytics
