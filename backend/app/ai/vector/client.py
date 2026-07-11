from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import httpx


@dataclass
class QdrantConfig:
    url: str = "http://localhost:6333"
    api_key: str | None = None
    prefer_grpc: bool = False
    timeout: int = 30


class QdrantClientWrapper:
    def __init__(self, config: QdrantConfig) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers: dict[str, str] = {"Content-Type": "application/json"}
            if self._config.api_key:
                headers["api-key"] = self._config.api_key
            self._client = httpx.AsyncClient(
                base_url=self._config.url,
                headers=headers,
                timeout=self._config.timeout,
            )
        return self._client

    async def collection_exists(self, name: str) -> bool:
        client = await self._get_client()
        response = await client.get(f"/collections/{name}")
        return response.is_success

    async def create_collection(self, name: str, config: dict[str, Any]) -> bool:
        client = await self._get_client()
        response = await client.put(f"/collections/{name}", json=config)
        return response.is_success

    async def delete_collection(self, name: str) -> bool:
        client = await self._get_client()
        response = await client.delete(f"/collections/{name}")
        return response.is_success

    async def list_collections(self) -> list[str]:
        client = await self._get_client()
        response = await client.get("/collections")
        response.raise_for_status()
        data = response.json()
        return [c["name"] for c in data.get("result", {}).get("collections", [])]

    async def upsert(self, collection: str, points: list[dict[str, Any]]) -> bool:
        client = await self._get_client()
        response = await client.put(
            f"/collections/{collection}/points",
            json={"points": points},
        )
        return response.is_success

    async def search(
        self, collection: str, query_vector: list[float], limit: int = 20,
        score_threshold: float | None = None, query_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        client = await self._get_client()
        payload: dict[str, Any] = {
            "vector": query_vector,
            "limit": limit,
            "with_payload": True,
            "with_vector": False,
        }
        if score_threshold is not None:
            payload["score_threshold"] = score_threshold
        if query_filter:
            payload["filter"] = query_filter
        response = await client.post(
            f"/collections/{collection}/points/search", json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return cast("list[dict[str, Any]]", data.get("result", []))

    async def delete_points(self, collection: str, point_ids: list[str]) -> bool:
        client = await self._get_client()
        response = await client.post(
            f"/collections/{collection}/points/delete",
            json={"points": point_ids},
        )
        return response.is_success

    async def update_points(
        self, collection: str, points: list[dict[str, Any]]
    ) -> bool:
        return await self.upsert(collection, points)

    async def scroll(
        self, collection: str, limit: int = 100, offset: str | None = None,
        with_payload: bool = True, with_vectors: bool = False,
    ) -> tuple[list[dict[str, Any]], str | None]:
        client = await self._get_client()
        payload: dict[str, Any] = {
            "limit": limit,
            "with_payload": with_payload,
            "with_vector": with_vectors,
        }
        if offset:
            payload["offset"] = offset
        response = await client.post(
            f"/collections/{collection}/points/scroll", json=payload,
        )
        response.raise_for_status()
        data = response.json()
        result = data.get("result", {})
        points = result.get("points", [])
        next_offset = result.get("next_page_offset")
        return points, next_offset

    async def count(self, collection: str) -> int:
        client = await self._get_client()
        response = await client.post(
            f"/collections/{collection}/points/count", json={},
        )
        response.raise_for_status()
        data = response.json()
        return cast(int, data.get("result", {}).get("count", 0))

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
