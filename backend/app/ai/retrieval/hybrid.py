from __future__ import annotations

from typing import Any

from app.ai.retrieval.retriever import BaseRetriever, RetrieverResult


class HybridRetriever(BaseRetriever):
    def __init__(
        self,
        retrievers: list[tuple[BaseRetriever, float]],
    ) -> None:
        self._retrievers = retrievers

    async def retrieve(
        self, query: str, limit: int = 10, **kwargs: Any
    ) -> list[RetrieverResult]:
        all_results: list[RetrieverResult] = []
        seen: set[str] = set()

        for retriever, weight in self._retrievers:
            results = await retriever.retrieve(query, limit=limit * 2, **kwargs)
            for r in results:
                dedup_key = f"{r.source}:{r.metadata.get('id', r.content[:50])}"
                if dedup_key not in seen:
                    seen.add(dedup_key)
                    r.score *= weight
                    all_results.append(r)

        all_results.sort(key=lambda r: r.score, reverse=True)
        return all_results[:limit]

    async def retrieve_with_scores(
        self, query: str, limit: int = 10, **kwargs: Any
    ) -> list[tuple[RetrieverResult, list[tuple[str, float]]]]:
        all_results: list[tuple[RetrieverResult, list[tuple[str, float]]]] = []
        seen: set[str] = set()

        for retriever, weight in self._retrievers:
            results = await retriever.retrieve(query, limit=limit * 2, **kwargs)
            for r in results:
                dedup_key = f"{r.source}:{r.metadata.get('id', r.content[:50])}"
                if dedup_key not in seen:
                    seen.add(dedup_key)
                    all_results.append((r, [(retriever.__class__.__name__, weight)]))

        all_results.sort(key=lambda x: x[0].score, reverse=True)
        return all_results[:limit]
