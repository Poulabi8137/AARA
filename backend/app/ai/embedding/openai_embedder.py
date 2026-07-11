from __future__ import annotations

import httpx

from app.ai.embedding.interface import BaseEmbedder, EmbeddingConfig, EmbeddingResult


class OpenAIEmbedder(BaseEmbedder):
    provider_id = "openai"
    model = "text-embedding-3-small"
    dimension = 1536
    max_input_tokens = 8192
    is_local = False

    def __init__(self, api_key: str, config: EmbeddingConfig | None = None) -> None:
        super().__init__(config)
        self._api_key = api_key
        self._model = (config.model if config else None) or self.model

    async def embed(self, text: str) -> EmbeddingResult:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self._model, "input": text},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            vector: list[float] = data["data"][0]["embedding"]
        return EmbeddingResult(vector=vector, model=self._model, dimension=len(vector))

    async def embed_query(self, query: str) -> EmbeddingResult:
        return await self.embed(query)
