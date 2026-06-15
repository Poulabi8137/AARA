from __future__ import annotations

from typing import Any

from app.agents.retrieval_ranking import compute_content_hash, is_near_duplicate


class DedupResult:
    def __init__(self) -> None:
        self.removed_count: int = 0
        self._seen_ids: set[str] = set()
        self._seen_hashes: dict[int, str] = {}  # hash -> actual content
        self._seen_sources: set[str] = set()

    def is_duplicate(self, chunk: dict[str, Any]) -> bool:
        chunk_id = chunk.get("chunk_id", "") or str(hash(chunk.get("content", "")))
        content = chunk.get("content", "")
        chunk.get("source", "") or chunk.get("metadata", {}).get("source", "")

        if chunk_id and chunk_id in self._seen_ids:
            self.removed_count += 1
            return True

        h = compute_content_hash(content)
        if h in self._seen_hashes:
            self.removed_count += 1
            return True

        # Near-dup check against stored content
        for existing_hash, existing_content in self._seen_hashes.items():
            if is_near_duplicate(content, existing_content):
                self.removed_count += 1
                return True

        self._seen_ids.add(chunk_id)
        self._seen_hashes[h] = content
        return False

    def total_removed(self) -> int:
        return self.removed_count


def deduplicate_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove identical, near-duplicate, and same-source duplicates."""
    deduper = DedupResult()
    seen_sources: dict[str, list[dict[str, Any]]] = {}

    for chunk in chunks:
        source = chunk.get("source", "") or chunk.get("metadata", {}).get("source", "")
        if source:
            seen_sources.setdefault(source, []).append(chunk)

    for source, src_chunks in seen_sources.items():
        if len(src_chunks) < 2:
            continue
        src_chunks.sort(key=lambda c: c.get("relevance_score", 0), reverse=True)
        for other in src_chunks[1:]:
            if is_near_duplicate(src_chunks[0].get("content", ""), other.get("content", "")):
                deduper.removed_count += 1

    result: list[dict[str, Any]] = []
    for chunk in chunks:
        if not deduper.is_duplicate(chunk):
            result.append(chunk)
    return result
