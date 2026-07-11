from __future__ import annotations

import logging
from typing import Any

from app.ai.embedding.interface import BaseEmbedder
from app.ai.retrieval.retriever import BaseRetriever, RetrieverResult
from app.ai.vector.client import QdrantClientWrapper, QdrantConfig

logger = logging.getLogger(__name__)


class QdrantRetriever(BaseRetriever):
    """Retrieves documents from Qdrant using semantic similarity search."""

    def __init__(
        self,
        embedder: BaseEmbedder,
        collection: str = "papers",
        qdrant_url: str = "http://localhost:6333",
        qdrant_api_key: str | None = None,
    ) -> None:
        self._embedder = embedder
        self._collection = collection
        self._client = QdrantClientWrapper(
            QdrantConfig(url=qdrant_url, api_key=qdrant_api_key)
        )

    async def retrieve(
        self, query: str, limit: int = 10, **kwargs: Any
    ) -> list[RetrieverResult]:
        try:
            embedding = await self._embedder.embed_query(query)
            raw = await self._client.search(
                collection=self._collection,
                query_vector=embedding.vector,
                limit=limit,
                score_threshold=kwargs.get("score_threshold"),
            )
        except Exception:
            logger.warning("Qdrant retrieval failed; returning empty results", exc_info=True)
            return []

        results: list[RetrieverResult] = []
        for hit in raw:
            payload: dict[str, Any] = hit.get("payload") or {}
            results.append(
                RetrieverResult(
                    content=payload.get("content") or payload.get("abstract") or "",
                    score=float(hit.get("score", 0.0)),
                    source="qdrant",
                    metadata={
                        "id": str(hit.get("id", "")),
                        "title": payload.get("title", ""),
                        "doi": payload.get("doi", ""),
                        "url": payload.get("url", ""),
                        "authors": payload.get("authors", []),
                        "year": payload.get("year", 0),
                        "citation_count": payload.get("citation_count", 0),
                    },
                )
            )
        return results
