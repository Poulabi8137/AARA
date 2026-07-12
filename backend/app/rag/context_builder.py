from __future__ import annotations

from app.core.logging import get_logger
from app.rag.config import get_rag_settings
from app.rag.models import (
    ContextChunk,
    RAGContext,
    RetrievedEvidence,
)

logger = get_logger("rag.context_builder")
settings = get_rag_settings()


class ContextBuilder:
    def build(
        self,
        evidence: list[RetrievedEvidence],
        budget_tokens: int | None = None,
    ) -> RAGContext:
        budget = budget_tokens or settings.context_max_tokens
        chunk_limit = settings.context_chunk_max_tokens
        dedup_enabled = settings.context_deduplication_enabled
        dedup_threshold = settings.context_deduplication_similarity

        chunks: list[ContextChunk] = []
        total_tokens = 0
        seen_sources: set[str] = set()
        truncated = False

        for ev in evidence:
            if total_tokens >= budget:
                truncated = True
                break

            token_count = self._estimate_tokens(ev.content)
            if token_count > chunk_limit:
                token_count = chunk_limit

            if dedup_enabled:
                dedup_key = ev.content.strip()[:100]
                if dedup_key in seen_sources:
                    continue
                seen_sources.add(dedup_key)

            citation = self._make_citation(ev)

            chunk = ContextChunk(
                content=ev.content[:chunk_limit] if len(ev.content) > chunk_limit else ev.content,
                source_type=ev.source_type,
                source_id=ev.source_id,
                score=ev.score,
                rank=ev.rank,
                citation=citation,
                token_count=token_count,
            )
            chunks.append(chunk)
            total_tokens += token_count

            if total_tokens >= budget:
                truncated = True
                break

        sources = sorted({c.citation or c.source_id for c in chunks if c.citation or c.source_id})

        logger.info(
            "context built",
            extra={
                "chunks": len(chunks),
                "total_tokens": total_tokens,
                "budget": budget,
                "truncated": truncated,
                "unique_sources": len(sources),
            },
        )

        return RAGContext(
            chunks=chunks,
            total_tokens=total_tokens,
            budget_tokens=budget,
            truncated=truncated,
            sources=sources,
        )

    def _estimate_tokens(self, text: str) -> int:
        return len(text.split())

    def _make_citation(self, ev: RetrievedEvidence) -> str | None:
        parts: list[str] = []
        if ev.metadata.get("source_paper_title"):
            parts.append(ev.metadata["source_paper_title"])
        if ev.metadata.get("source"):
            parts.append(f"({ev.metadata['source']})")
        if ev.metadata.get("title"):
            parts.append(ev.metadata["title"])
        return " – ".join(parts) if parts else None
