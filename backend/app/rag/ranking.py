from __future__ import annotations

import time
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.rag.config import get_rag_settings
from app.rag.models import RetrievedEvidence, SourceType

logger = get_logger("rag.ranking")
settings = get_rag_settings()

_SOURCE_PRIORITY: dict[SourceType, float] = {
    SourceType.CHROMA_PAPER: 1.0,
    SourceType.CHROMA_CITATION: 0.95,
    SourceType.CHROMA_KNOWLEDGE: 0.9,
    SourceType.MEMORY_LONG_TERM: 0.85,
    SourceType.MEMORY_PAPER: 0.85,
    SourceType.CHROMA_REPORT: 0.8,
    SourceType.MEMORY_PROJECT: 0.75,
    SourceType.CHROMA_WEB: 0.7,
    SourceType.MEMORY_SESSION: 0.65,
}


class RankingEngine:
    def __init__(
        self,
        source_weights: dict[SourceType, float] | None = None,
    ):
        self._source_weights = source_weights or _SOURCE_PRIORITY
        self._freshness_decay_days = settings.ranking_freshness_decay_days
        self._semantic_weight = settings.ranking_semantic_weight
        self._source_weight_factor = settings.ranking_source_weight
        self._freshness_weight = settings.ranking_freshness_weight
        self._confidence_weight = settings.ranking_confidence_weight
        self._rerank_top_k = settings.retrieval_rerank_top_k

    def rerank(
        self,
        evidence: list[RetrievedEvidence],
        top_k: int | None = None,
    ) -> list[RetrievedEvidence]:
        start = time.monotonic()
        k = top_k or self._rerank_top_k or len(evidence)

        for ev in evidence:
            ev.freshness_score = self._compute_freshness(ev)
            ev.source_priority = self._source_priority_score(ev)
            ev.score = self._compute_final_score(ev)

        evidence.sort(key=lambda e: e.score, reverse=True)

        result = evidence[:k]
        for i, ev in enumerate(result):
            ev.rank = i + 1

        logger.info(
            "ranking complete",
            extra={
                "input": len(evidence),
                "output": len(result),
                "top_score": round(result[0].score, 4) if result else 0.0,
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return result

    def _compute_freshness(self, ev: RetrievedEvidence) -> float:
        if self._freshness_decay_days <= 0:
            return 1.0
        ts_str = ev.metadata.get("created_at") or ev.metadata.get("timestamp") or ""
        if not ts_str:
            return 0.8
        try:
            created = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - created).days
            decay = max(0.0, 1.0 - (age_days / self._freshness_decay_days))
            return round(decay, 4)
        except (ValueError, TypeError):
            return 0.8

    def _source_priority_score(self, ev: RetrievedEvidence) -> int:
        priority = self._source_weights.get(ev.source_type, 0.5)
        return int(priority * 10)

    def _compute_final_score(self, ev: RetrievedEvidence) -> float:
        semantic = max(0.0, ev.score)
        source_val = ev.source_priority / 10.0
        freshness = ev.freshness_score
        confidence = ev.metadata.get("confidence", 0.5)
        if isinstance(confidence, str):
            try:
                confidence = float(confidence)
            except (ValueError, TypeError):
                confidence = 0.5
        confidence = max(0.0, min(1.0, float(confidence)))

        score = (
            self._semantic_weight * semantic
            + self._source_weight_factor * source_val
            + self._freshness_weight * freshness
            + self._confidence_weight * confidence
        )
        return round(score, 4)
