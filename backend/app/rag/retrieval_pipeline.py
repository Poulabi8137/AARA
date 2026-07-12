from __future__ import annotations

import time

from app.core.logging import get_logger
from app.rag.collection_router import CollectionRouter
from app.rag.evidence_fusion import EvidenceFusion
from app.rag.citation_retriever import CitationRetriever
from app.rag.config import get_rag_settings
from app.rag.models import (
    ProcessedQuery,
    RetrievedEvidence,
    RetrievalOutput,
    RoutingStrategy,
)
from app.rag.ranking import RankingEngine
from app.rag.retrieval_engine import RetrievalEngine

logger = get_logger("rag.retrieval_pipeline")
settings = get_rag_settings()


class RetrievalPipeline:
    def __init__(
        self,
        engine: RetrievalEngine,
        router: CollectionRouter | None = None,
        ranker: RankingEngine | None = None,
        fusion: EvidenceFusion | None = None,
        citation_retriever: CitationRetriever | None = None,
    ):
        self._engine = engine
        self._router = router or CollectionRouter()
        self._ranker = ranker or RankingEngine()
        self._fusion = fusion or EvidenceFusion()
        self._citation_retriever = citation_retriever

    async def execute(
        self,
        query: ProcessedQuery,
        routing_strategy: RoutingStrategy | None = None,
    ) -> RetrievalOutput:
        start = time.monotonic()

        route = self._router.route(query, strategy=routing_strategy)
        logger.info(
            "collection route selected",
            extra={
                "strategy": route.strategy.value,
                "label": route.label,
                "collections": len(route.collections),
            },
        )

        all_evidence, collections_analytics = await self._engine.retrieve(
            query=query,
            route_collections=route.collections,
        )
        candidates = len(all_evidence)

        deduped = self._deduplicate(all_evidence)
        duplicates = candidates - len(deduped)

        fused = self._fusion.fuse(deduped)
        fused_count = len(fused)

        reranked = self._ranker.rerank(fused, top_k=settings.retrieval_rerank_top_k)

        if self._citation_retriever:
            reranked = await self._citation_retriever.fetch_citations(
                reranked,
                top_k=settings.citation_max_per_query,
            )

        for i, ev in enumerate(reranked):
            ev.rank = i + 1

        semantic_count = sum(1 for e in all_evidence if e.score > 0.0)
        keyword_count = candidates - semantic_count

        collection_stats = {
            "route_strategy": route.strategy.value,
            "route_label": route.label,
            "collections_count": len(route.collections),
            "platform_hits": sum(a.hits for a in collections_analytics),
            "platform_latency_ms": sum(a.latency_ms for a in collections_analytics),
        }

        confidence = self._calculate_confidence(reranked)
        duration = time.monotonic() - start

        logger.info(
            "retrieval pipeline complete",
            extra={
                "candidates": candidates,
                "duplicates_removed": duplicates,
                "after_dedup": len(deduped),
                "after_fusion": fused_count,
                "final": len(reranked),
                "confidence": round(confidence, 3),
                "duration": round(duration, 3),
            },
        )

        return RetrievalOutput(
            query=query,
            evidence=reranked,
            total_candidates=candidates,
            semantic_results=semantic_count,
            keyword_results=keyword_count,
            duplicates_removed=duplicates,
            confidence=confidence,
            duration_seconds=duration,
            collections_searched=collections_analytics,
            collection_stats=collection_stats,
        )

    def _deduplicate(
        self, evidence: list[RetrievedEvidence]
    ) -> list[RetrievedEvidence]:
        seen_content: set[str] = set()
        seen_ids: set[str] = set()
        result: list[RetrievedEvidence] = []
        for ev in evidence:
            content_dedup = ev.content.strip()[:200]
            if content_dedup not in seen_content and ev.source_id not in seen_ids:
                seen_content.add(content_dedup)
                seen_ids.add(ev.source_id)
                result.append(ev)
        return result

    def _calculate_confidence(
        self, evidence: list[RetrievedEvidence]
    ) -> float:
        if not evidence:
            return 0.0
        scores = [e.score for e in evidence if e.score > 0]
        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 4)
