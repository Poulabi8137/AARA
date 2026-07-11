from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

from app.ai.vector.client import QdrantClientWrapper


@dataclass
class CollectionConfig:
    dimension: int = 384
    distance: str = "Cosine"
    hnsw_m: int = 16
    hnsw_ef_construct: int = 100
    quantization: str | None = "int8"
    payload_indexes: list[dict[str, Any]] = field(default_factory=list)


class CollectionManager:
    REQUIRED_PAYLOAD_INDEXES = [
        {"field_name": "workspace_id", "field_type": "keyword"},
        {"field_name": "paper_id", "field_type": "keyword"},
        {"field_name": "model_id", "field_type": "keyword"},
        {"field_name": "section_name", "field_type": "keyword"},
    ]

    def __init__(self, client: QdrantClientWrapper) -> None:
        self._client = client

    async def ensure_collection(
        self, name: str, config: CollectionConfig | None = None
    ) -> bool:
        cfg = config or CollectionConfig()
        if await self._client.collection_exists(name):
            return True

        vectors_config: dict[str, Any] = {
            "size": cfg.dimension,
            "distance": cfg.distance,
            "hnsw_config": {
                "m": cfg.hnsw_m,
                "ef_construct": cfg.hnsw_ef_construct,
            },
        }

        collection_config: dict[str, Any] = {
            "vectors": vectors_config,
        }

        if cfg.quantization == "int8":
            collection_config["quantization_config"] = {
                "scalar": {
                    "type": "int8",
                    "always_ram": True,
                }
            }

        created = await self._client.create_collection(name, collection_config)
        if created:
            indexes = cfg.payload_indexes or self.REQUIRED_PAYLOAD_INDEXES
            for index in indexes:
                await self._client._get_client()  # ensure client exists
                client = await self._client._get_client()
                from contextlib import suppress
                with suppress(Exception):
                    await client.put(
                        f"/collections/{name}/index",
                        json={
                            "field_name": index["field_name"],
                            "field_type": index.get("field_type", "keyword"),
                        },
                    )
        return created

    async def delete_collection(self, name: str) -> bool:
        return await self._client.delete_collection(name)

    async def list_collections(self) -> list[str]:
        return await self._client.list_collections()

    async def collection_info(self, name: str) -> dict[str, Any] | None:
        client = await self._client._get_client()
        response = await client.get(f"/collections/{name}")
        if response.is_success:
            return cast("dict[str, Any]", response.json().get("result"))
        return None

    @staticmethod
    def get_collection_name(model_id: str) -> str:
        safe = model_id.replace("/", "_").replace("-", "_")
        return f"vectors_{safe}"
