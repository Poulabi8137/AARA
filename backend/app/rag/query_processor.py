from __future__ import annotations

import re
import uuid
from typing import Any

from app.core.logging import get_logger
from app.rag.models import (
    ProcessedQuery,
    RetrievalStrategy,
    SearchIntent,
)

logger = get_logger("rag.query_processor")

_RESEARCH_QUESTION_PATTERNS: list[tuple[re.Pattern, SearchIntent]] = [
    (re.compile(r"\b(what|how|why|when|where)\b.*\?", re.IGNORECASE), SearchIntent.FACTUAL),
    (re.compile(r"\bcompare|contrast|difference|similarities?\b", re.IGNORECASE), SearchIntent.COMPARATIVE),
    (re.compile(r"\bexplore|overview|survey|review\b", re.IGNORECASE), SearchIntent.EXPLORATORY),
    (re.compile(r"\bmethod|approach|technique|algorithm\b", re.IGNORECASE), SearchIntent.METHODOLOGICAL),
    (re.compile(r"\blimit|drawback|critique|challenge|problem\b", re.IGNORECASE), SearchIntent.CRITICAL),
    (re.compile(r"\bsummarize|summary|abstract|synthesize\b", re.IGNORECASE), SearchIntent.SUMMARIZATION),
]

_STOP_WORDS: set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "out", "off", "over", "under", "again",
    "further", "then", "once", "here", "there", "when", "where",
    "why", "how", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "just", "it", "its",
    "this", "that", "these", "those", "about", "up", "what", "which",
    "who", "and", "but", "or", "if", "because",
}


class QueryProcessor:
    def process(
        self,
        query: str,
        user_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        top_k: int | None = None,
        intent_override: SearchIntent | None = None,
    ) -> ProcessedQuery:
        normalized = self._normalize(query)
        intent = intent_override or self._detect_intent(normalized)
        keywords = self._extract_keywords(normalized)
        metadata_filters = self._extract_metadata_filters(raw=query, normalized=normalized)
        strategies = self._select_strategies(intent)
        rewritten = self._rewrite(normalized, intent)

        return ProcessedQuery(
            raw=query,
            normalized=normalized,
            rewritten=rewritten,
            intent=intent,
            keywords=keywords,
            metadata_filters=metadata_filters,
            search_strategies=strategies,
            user_id=user_id,
            project_id=project_id,
            top_k=top_k or 10,
        )

    def _normalize(self, query: str) -> str:
        q = query.strip()
        q = re.sub(r"\s+", " ", q)
        return q

    def _detect_intent(self, normalized: str) -> SearchIntent:
        for pattern, intent in _RESEARCH_QUESTION_PATTERNS:
            if pattern.search(normalized):
                return intent
        return SearchIntent.FACTUAL

    def _extract_keywords(self, normalized: str) -> list[str]:
        tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", normalized)
        tokens = [t.lower() for t in tokens if t.lower() not in _STOP_WORDS]
        seen: set[str] = set()
        result: list[str] = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                result.append(t)
        return result

    def _extract_metadata_filters(
        self, raw: str, normalized: str
    ) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        year_match = re.search(r"\b(19|20)\d{2}\b", normalized)
        if year_match:
            filters["year"] = int(year_match.group(0))
        doi_match = re.search(r"10\.\d{4,}/[-._;()/:A-Za-z0-9]+", raw)
        if doi_match:
            filters["doi"] = doi_match.group(0)
        return filters

    def _select_strategies(self, intent: SearchIntent) -> list[RetrievalStrategy]:
        if intent in (SearchIntent.FACTUAL, SearchIntent.METHODOLOGICAL, SearchIntent.COMPARATIVE):
            return [RetrievalStrategy.HYBRID, RetrievalStrategy.SEMANTIC]
        if intent == SearchIntent.SUMMARIZATION:
            return [RetrievalStrategy.SEMANTIC]
        return [RetrievalStrategy.HYBRID]

    def _rewrite(self, normalized: str, intent: SearchIntent) -> str:
        if intent == SearchIntent.COMPARATIVE:
            terms = re.split(r"\b(?:vs\.?|versus|compare|and|or)\b", normalized, flags=re.IGNORECASE)
            if len(terms) >= 2:
                return " ".join(t.strip() for t in terms if t.strip())
        return normalized
