from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ai.embedding.interface import BaseEmbedder
from app.ai.vector.client import QdrantClientWrapper


@dataclass
class SearchResultItem:
    id: str
    score: float
    payload: dict[str, Any] = field(default_factory=dict)
    vector: list[float] | None = None


class VectorSearch:
    def __init__(self, client: QdrantClientWrapper) -> None:
        self._client = client

    async def search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int = 20,
        score_threshold: float | None = None,
        workspace_id: str | None = None,
        filter_kwargs: dict[str, Any] | None = None,
    ) -> list[SearchResultItem]:
        query_filter = None
        must_conditions: list[dict[str, Any]] = []

        if workspace_id:
            must_conditions.append({
                "key": "workspace_id",
                "match": {"value": workspace_id},
            })

        if filter_kwargs:
            for key, value in filter_kwargs.items():
                must_conditions.append({
                    "key": key,
                    "match": {"value": str(value)},
                })

        if must_conditions:
            query_filter = {"must": must_conditions}

        results = await self._client.search(
            collection=collection,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter,
        )

        return [
            SearchResultItem(
                id=r.get("id", ""),
                score=r.get("score", 0.0),
                payload=r.get("payload", {}),
                vector=r.get("vector"),
            )
            for r in results
        ]

    async def search_by_text(
        self,
        collection: str,
        query: str,
        embedder: BaseEmbedder,
        limit: int = 20,
        score_threshold: float | None = None,
        workspace_id: str | None = None,
        filter_kwargs: dict[str, Any] | None = None,
    ) -> list[SearchResultItem]:
        result = await embedder.embed_query(query)
        return await self.search(
            collection=collection,
            query_vector=result.vector,
            limit=limit,
            score_threshold=score_threshold,
            workspace_id=workspace_id,
            filter_kwargs=filter_kwargs,
        )

    async def batch_insert(
        self,
        collection: str,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
        ids: list[str] | None = None,
    ) -> bool:
        import uuid
        points = []
        for i, vec in enumerate(vectors):
            points.append({
                "id": ids[i] if ids else str(uuid.uuid4()),
                "vector": vec,
                "payload": payloads[i] if i < len(payloads) else {},
            })
        return await self._client.upsert(collection, points)

    async def delete(self, collection: str, point_ids: list[str]) -> bool:
        return await self._client.delete_points(collection, point_ids)

    async def update(
        self,
        collection: str,
        point_id: str,
        vector: list[float] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> bool:
        point: dict[str, Any] = {"id": point_id}
        if vector is not None:
            point["vector"] = vector
        if payload is not None:
            point["payload"] = payload
        return await self._client.update_points(collection, [point])
