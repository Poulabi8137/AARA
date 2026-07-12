from __future__ import annotations

import time
import uuid
from typing import Any

from app.core.logging import get_logger
from app.rag.config import get_rag_settings
from app.rag.models import RetrievedEvidence, SourceType

logger = get_logger("rag.citation_retriever")
settings = get_rag_settings()


class CitationRetriever:
    def __init__(self, vectorstore: Any):
        self._vectorstore = vectorstore
        self._citation_collection_max = settings.citation_max_per_query
        self._citation_score_threshold = settings.citation_score_threshold

    async def fetch_citations(
        self,
        evidence: list[RetrievedEvidence],
        top_k: int | None = None,
    ) -> list[RetrievedEvidence]:
        start = time.monotonic()
        k = top_k or self._citation_collection_max

        paper_evidence = [
            ev for ev in evidence
            if ev.source_type in {
                SourceType.CHROMA_PAPER,
                SourceType.MEMORY_PAPER,
            }
        ]

        if not paper_evidence:
            return evidence

        citation_queries = []
        for ev in paper_evidence:
            paper_title = ev.metadata.get("title", "") or ev.metadata.get("paper_title", "")
            if paper_title:
                citation_queries.append(paper_title[:200])
            elif ev.content:
                citation_queries.append(ev.content[:200])

        if not citation_queries:
            return evidence

        try:
            collection = await self._vectorstore.get_collection("citations")
        except Exception:
            logger.warning("citations collection not found")
            return evidence

        all_citations: list[RetrievedEvidence] = []
        seen_content: set[str] = set()

        for query_text in citation_queries:
            try:
                results = collection.similarity_search_with_relevance_scores(
                    query=query_text,
                    k=k,
                )
            except Exception as exc:
                logger.debug("citation search failed", extra={"error": str(exc)})
                continue

            for doc, score in results:
                if score < self._citation_score_threshold:
                    continue
                content = doc.page_content[:500].strip()
                if not content or content in seen_content:
                    continue
                seen_content.add(content)
                citation = RetrievedEvidence(
                    content=content,
                    source_type=SourceType.CHROMA_CITATION,
                    source_id=str(uuid.uuid4()),
                    score=score,
                    metadata={
                        **doc.metadata,
                        "citation_query": query_text,
                        "attached_to": query_text,
                    },
                    provenance=f"citation: {query_text[:80]}",
                )
                all_citations.append(citation)

        if all_citations:
            evidence.extend(all_citations)
            logger.info(
                "citation retrieval complete",
                extra={
                    "paper_evidence": len(paper_evidence),
                    "citations_found": len(all_citations),
                    "duration_ms": round((time.monotonic() - start) * 1000, 1),
                },
            )

        return evidence
