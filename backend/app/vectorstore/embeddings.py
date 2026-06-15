from __future__ import annotations

from typing import Protocol, runtime_checkable



@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol that all embedding providers must implement.

    Enables swapping sentence-transformers, OpenAI, Voyage, Gemini,
    or BGE models without changing the retrieval pipeline.
    """

    model_name: str
    dimensions: int

    async def embed_text(self, text: str) -> list[float]:
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...

    async def embed_query(self, query: str) -> list[float]:
        ...


class MiniLMEmbeddingProvider:
    """Default embedding provider using sentence-transformers/all-MiniLM-L6-v2.

    Loads the model once on first call and reuses it for all embeddings.
    """

    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimensions: int = 384

    def __init__(self) -> None:
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    async def embed_text(self, text: str) -> list[float]:
        model = self._get_model()
        emb = model.encode(text, show_progress_bar=False)
        return emb.tolist()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        embeddings = model.encode(texts, show_progress_bar=False)
        return [e.tolist() for e in embeddings]

    async def embed_query(self, query: str) -> list[float]:
        return await self.embed_text(query)


class OpenAIEmbeddingProvider:
    """OpenAI embedding provider for swapping later."""

    model_name: str = "text-embedding-3-small"
    dimensions: int = 1536

    def __init__(self, api_key: str, model: str | None = None) -> None:
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=api_key)
        if model:
            self.model_name = model

    async def embed_text(self, text: str) -> list[float]:
        resp = await self._client.embeddings.create(
            model=self.model_name, input=text
        )
        return resp.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.embeddings.create(
            model=self.model_name, input=texts
        )
        sorted_data = sorted(resp.data, key=lambda x: x.index)
        return [d.embedding for d in sorted_data]

    async def embed_query(self, query: str) -> list[float]:
        return await self.embed_text(query)
