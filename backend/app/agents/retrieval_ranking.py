from __future__ import annotations

import re
from typing import Any


def compute_relevance_score(
    content: str,
    query: str,
    semantic_score: float,
    source_quality: float = 50.0,
    metadata_match: float = 0.0,
    freshness_days: float | None = None,
) -> float:
    """Composite relevance score 0-100 combining multiple signals."""
    keyword_score = _keyword_overlap(content, query) * 40.0
    semantic_weighted = semantic_score * 30.0
    quality_weighted = (source_quality / 100.0) * 15.0
    metadata_weighted = (metadata_match / 100.0) * 10.0
    freshness_weighted = _freshness_score(freshness_days) * 5.0

    raw = keyword_score + semantic_weighted + quality_weighted + metadata_weighted + freshness_weighted
    return round(min(100.0, max(0.0, raw)), 2)


def _keyword_overlap(content: str, query: str) -> float:
    """Jaccard-like keyword overlap ratio."""
    content_lower = content.lower()
    query_terms = set(re.findall(r"\b[a-z0-9]{3,}\b", query.lower()))

    if not query_terms:
        return 0.0

    matches = sum(1 for t in query_terms if t in content_lower)
    return matches / len(query_terms)


def _freshness_score(freshness_days: float | None) -> float:
    if freshness_days is None:
        return 0.5
    if freshness_days <= 30:
        return 1.0
    if freshness_days <= 180:
        return 0.8
    if freshness_days <= 365:
        return 0.5
    return 0.2


def compute_source_quality(metadata: dict[str, Any]) -> float:
    """Heuristic source quality based on metadata fields."""
    score = 50.0
    if metadata.get("source") and metadata["source"] not in ("unknown", "mock", ""):
        score += 10
    if metadata.get("author"):
        score += 10
    if metadata.get("page_number") is not None:
        score += 5
    if metadata.get("filename"):
        score += 5
    if metadata.get("chunk_index") is not None:
        score += 5
    char_count = len(metadata.get("content", "") or "")
    if char_count > 200:
        score += 10
    if char_count > 500:
        score += 5
    return min(100.0, score)


def compute_content_hash(content: str) -> int:
    """Simple hash for dedup comparison."""
    cleaned = re.sub(r"\s+", " ", content.strip().lower())
    return hash(cleaned[:500])


def is_near_duplicate(content_a: str, content_b: str, threshold: float = 0.65) -> bool:
    """Rough near-dup check via character trigram overlap."""
    def trigrams(text: str) -> set[str]:
        cleaned = re.sub(r"\s+", " ", text.lower()).strip()
        return {cleaned[i:i+3] for i in range(len(cleaned) - 2)}

    trigs_a = trigrams(content_a)
    trigs_b = trigrams(content_b)

    if not trigs_a or not trigs_b:
        return content_a.strip().lower() == content_b.strip().lower()

    intersection = trigs_a & trigs_b
    union = trigs_a | trigs_b
    jaccard = len(intersection) / len(union)
    return jaccard >= threshold
