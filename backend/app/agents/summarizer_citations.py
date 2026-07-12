from __future__ import annotations

import re
from collections import Counter
from typing import Any

from app.schemas.summarizer import CitationRecord


def extract_key_phrases(text: str, top_n: int = 5) -> list[str]:
    """Extract the most frequent meaningful phrases from text."""
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    stopwords = {
        "this",
        "that",
        "with",
        "from",
        "have",
        "been",
        "were",
        "they",
        "their",
        "them",
        "would",
        "could",
        "should",
        "about",
        "which",
        "when",
        "where",
        "what",
        "also",
        "than",
        "then",
        "into",
        "more",
        "some",
        "such",
        "these",
        "those",
        "both",
        "each",
        "other",
        "over",
        "very",
        "just",
        "because",
        "after",
        "before",
        "between",
        "through",
        "during",
        "without",
        "within",
        "across",
        "being",
        "does",
        "done",
        "make",
        "made",
        "take",
        "told",
        "said",
        "came",
        "came",
        "like",
    }
    filtered = [w for w in words if w not in stopwords and len(w) > 3]
    counter = Counter(filtered)
    return [word for word, _ in counter.most_common(top_n)]


def extract_statistics(text: str) -> list[str]:
    """Extract numerical statistics from text."""
    patterns = [
        r"\b\d+(?:\.\d+)?%",
        r"\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:percent|percentage|points?)\b",
        r"\b(?:over|more than|less than|approximately|about|around)\s+\d+(?:\.\d+)?\b",
        r"\b\d+(?:\.\d+)?\s*(?:million|billion|trillion|thousand|hundred|x|times|fold)\b",
        r"\b[A-Z][a-z]+(?:\s+et\s+al\.)?\s*\(?\d{4}\)?\b",
    ]
    results: list[str] = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        results.extend(m.strip() for m in matches)
    return list(set(results))


def detect_contradictory_language(text: str) -> list[str]:
    """Detect statements likely containing contradictions."""
    signals = [
        r"(?:however|but|yet|nevertheless|nonetheless|although|though|on the other hand|"
        r"conversely|in contrast|alternatively|contrary to|while some|whereas|"
        r"despite|in spite of|rather than|instead of)"
    ]
    pattern = re.compile("|".join(signals), re.IGNORECASE)
    matches = pattern.findall(text)
    return list(set(m.strip() for m in matches))


def build_citation_index(evidence: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build a chunk_id -> metadata lookup from evidence."""
    index: dict[str, dict[str, Any]] = {}
    for chunk in evidence:
        cid = chunk.get("chunk_id", "") or str(hash(chunk.get("content", "")))
        index[cid] = {
            "content": chunk.get("content", ""),
            "source": chunk.get("source", ""),
            "query": chunk.get("query", ""),
            "collection": chunk.get("collection", ""),
        }
    return index


def compute_evidence_utilization(
    evidence_count: int,
    citations: list[CitationRecord],
    total_chunks: int,
) -> float:
    """What fraction of evidence chunks are cited at least once."""
    cited_ids: set[str] = set()
    for c in citations:
        cited_ids.update(c.supporting_chunk_ids)
    if total_chunks == 0:
        return 0.0
    return round(min(100.0, (len(cited_ids) / total_chunks) * 100), 2)


def compute_compression_ratio(original_len: int, summary_len: int) -> float:
    if original_len == 0:
        return 0.0
    return round(min(100.0, (summary_len / original_len) * 100), 2)
