from __future__ import annotations

from dataclasses import dataclass, field

from app.ai.retrieval.retriever import RetrieverResult


@dataclass
class ReRankerResult:
    results: list[RetrieverResult]
    scores: list[float] = field(default_factory=list)


class ReRanker:
    def __init__(self, model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self._model_name = model
        self._model = None

    async def re_rank(
        self, query: str, results: list[RetrieverResult], top_k: int = 20
    ) -> ReRankerResult:
        if not results:
            return ReRankerResult(results=[])

        if len(results) <= top_k:
            return ReRankerResult(results=results)

        if self._model is not None:
            try:
                pairs = [(query, r.content[:512]) for r in results]
                import asyncio
                scores = await asyncio.to_thread(self._model.predict, pairs)
                scored = list(zip(results, scores, strict=False))
                scored.sort(key=lambda x: x[1], reverse=True)
                reranked = [r for r, s in scored[:top_k]]
                final_scores = [float(s) for r, s in scored[:top_k]]
                return ReRankerResult(results=reranked, scores=final_scores)
            except Exception:
                pass

        results.sort(key=lambda r: r.score, reverse=True)
        return ReRankerResult(results=results[:top_k], scores=[r.score for r in results[:top_k]])

    async def score_pairs(
        self, pairs: list[tuple[str, str]]
    ) -> list[float]:
        if self._model is not None:
            try:
                import asyncio
                scores = await asyncio.to_thread(self._model.predict, pairs)
                return [float(s) for s in scores]
            except Exception:
                pass
        return [0.0] * len(pairs)
