from __future__ import annotations

import json
import time
from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry
from app.agents.state import ResearchState
from app.agents.retrieval_ranking import (
    compute_relevance_score,
    compute_source_quality,
)
from app.agents.retrieval_dedup import deduplicate_chunks
from app.schemas.retrieval import (
    RetrievedChunkSchema,
    RetrievalBundle,
    RetrievalMetrics,
    RetrievalDebugInfo,
)
from app.core.logging import get_logger

logger = get_logger("agents.retrieval")

ALL_COLLECTIONS = [
    "research_papers",
    "web_search_results",
    "citations",
    "knowledge_base",
    "generated_reports",
]

TOP_K_PER_COLLECTION = 10
MIN_SOURCES_PER_SUBTOPIC = 3
MAX_RETRIES = 2


@AgentRegistry.register
class RetrievalAgent(BaseAgent):
    agent_name = "retrieval"
    description = (
        "Multi-collection retrieval with ranking, dedup, bundling, coverage validation"
    )
    requires_human_approval = False

    async def arun(self, state: ResearchState) -> ResearchState:
        start = time.monotonic()
        query = state.get("query", "")
        planner_raw = state.get("planner_output")
        project_id = state.get("project_id", "")

        debug = RetrievalDebugInfo()
        metrics = RetrievalMetrics()

        # Parse planner output
        search_queries: list[str] = [query]
        subtopics: list[str] = []
        research_questions: list[str] = []

        if planner_raw and isinstance(planner_raw, str):
            try:
                plan = json.loads(planner_raw)
                planner_sq = plan.get("search_queries", [])
                planner_rq = plan.get("research_questions", [])
                planner_st = plan.get("subtopics", [])
                if planner_sq:
                    search_queries = planner_sq
                if planner_rq:
                    research_questions = planner_rq
                if planner_st:
                    subtopics = planner_st
            except (json.JSONDecodeError, TypeError):
                logger.warning("cannot parse planner_output, using fallback query")

        if not subtopics:
            subtopics = ["general"]

        debug.search_queries_used = list(search_queries) + research_questions[:2]

        # Execute multi-collection search for each query
        all_raw: list[dict[str, Any]] = []
        collection_hits: dict[str, int] = {}
        errors: list[str] = []

        queries_to_run = (search_queries + research_questions[:2])[:8]

        for q in queries_to_run:
            try:
                results = await self._search_collections(q, project_id)
                for col_name, col_result in results.items():
                    collection_hits[col_name] = (
                        collection_hits.get(col_name, 0) + col_result.total
                    )
                    for chunk in col_result.results:
                        metadata = dict(chunk.metadata) if chunk.metadata else {}
                        source_quality = compute_source_quality(metadata)
                        base_score = chunk.score if hasattr(chunk, "score") else 0.5
                        relevance = compute_relevance_score(
                            content=chunk.content,
                            query=q,
                            semantic_score=base_score,
                            source_quality=source_quality,
                            metadata_match=50.0,
                        )
                        all_raw.append(
                            {
                                "query": q,
                                "source": chunk.source,
                                "content": chunk.content,
                                "relevance_score": relevance,
                                "collection": col_name,
                                "metadata": metadata,
                                "retrieval_reason": f"matched query: {q[:60]}",
                                "chunk_id": chunk.chunk_id,
                            }
                        )
            except Exception as exc:
                logger.warning(
                    "search failed for query",
                    extra={"query": q[:40], "error": str(exc)},
                )
                errors.append(f"{q[:30]}: {str(exc)[:60]}")
                if len(errors) > MAX_RETRIES:
                    break

        debug.total_collections_searched = len(ALL_COLLECTIONS)
        debug.collection_hit_counts = dict(collection_hits)
        debug.documents_before_dedup = len(all_raw)

        if not all_raw:
            logger.warning("all collections returned empty, using fallback")
            metrics.used_fallback = True
            all_raw = self._fallback_results(query)
            debug.documents_before_dedup = len(all_raw)

        # Rank and deduplicate
        all_raw.sort(key=lambda c: c["relevance_score"], reverse=True)
        deduped = list(deduplicate_chunks(all_raw))
        debug.documents_after_dedup = len(deduped)
        debug.duplicates_removed = len(all_raw) - len(deduped)
        debug.errors = errors

        metrics.total_collections_searched = len(ALL_COLLECTIONS)
        metrics.collection_hit_counts = dict(collection_hits)
        metrics.documents_before_dedup = len(all_raw)
        metrics.documents_after_dedup = len(deduped)
        metrics.duplicates_removed = len(all_raw) - len(deduped)

        if deduped:
            scores = [d["relevance_score"] for d in deduped]
            metrics.average_relevance = round(sum(scores) / len(scores), 2)
            metrics.top_relevance = max(scores)

        # Build context bundles grouped by subtopic
        bundles: list[RetrievalBundle] = []
        for subtopic in subtopics:
            matched = [
                d for d in deduped if self._matches_subtopic(d["content"], subtopic)
            ]
            if not matched:
                matched = deduped[: min(3, len(deduped))]

            top_n = matched[: MIN_SOURCES_PER_SUBTOPIC + 2]
            evidence = [RetrievedChunkSchema(**d) for d in top_n]
            sources = list(set(e.source for e in evidence if e.source))
            avg_score = sum(e.relevance_score for e in evidence) / max(len(evidence), 1)

            bundle = RetrievalBundle(
                subtopic=subtopic,
                title=f"Evidence for: {subtopic}",
                evidence=evidence,
                sources=sources,
                confidence_score=round(avg_score, 2),
                coverage=len(evidence) >= MIN_SOURCES_PER_SUBTOPIC,
            )
            bundles.append(bundle)

        covered = sum(1 for b in bundles if b.coverage)
        metrics.coverage_ratio = round(covered / max(len(bundles), 1), 2)
        metrics.bundles = len(bundles)

        metrics.latency_seconds = round(time.monotonic() - start, 3)

        # Serialise into state
        state["retrieved_documents"] = [b.model_dump() for b in bundles]
        state["status"] = "retrieval_complete"
        state["agent_metrics"]["retrieval"] = metrics.model_dump()
        state["agent_metrics"]["retrieval_debug"] = debug.model_dump()

        logger.info(
            "retrieval complete",
            extra={
                "bundles": len(bundles),
                "deduped": len(deduped),
                "avg_relevance": metrics.average_relevance,
                "coverage": metrics.coverage_ratio,
                "latency": metrics.latency_seconds,
            },
        )

        return state

    # ── Private ────────────────────────────────────────

    async def _search_collections(self, query: str, project_id: str) -> dict[str, Any]:
        from app.vectorstore.retrieval import multi_collection_search

        try:
            return await multi_collection_search(
                query=query,
                collections=ALL_COLLECTIONS,  # type: ignore[list-item]
                project_id=project_id or None,
                top_k_per_collection=TOP_K_PER_COLLECTION,
            )
        except Exception:
            return {}

    def _matches_subtopic(self, content: str, subtopic: str) -> bool:
        words = subtopic.lower().split()
        content_lower = content.lower()
        return any(w in content_lower for w in words if len(w) > 3)

    def _fallback_results(self, query: str) -> list[dict[str, Any]]:
        """Generate simulated results when no real documents are available.

        These are clearly labeled as simulated for demo purposes.
        """
        simulated = [
            {
                "query": query,
                "source": "arXiv preprint",
                "content": f"[SIMULATED] Recent advances in {query} demonstrate significant progress in both theoretical foundations and practical applications. Key contributions include novel methodologies for addressing long-standing challenges in the field.",
                "relevance_score": 85.0,
                "collection": "knowledge_base",
                "metadata": {"source": "simulated_demo_data"},
                "retrieval_reason": "demo_simulation",
                "chunk_id": f"sim-{i}",
            }
            for i in range(3)
        ]
        return simulated
