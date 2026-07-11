from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmbeddingResult:
    vector: list[float]
    model: str = ""
    dimension: int = 0


@dataclass
class EmbeddingConfig:
    model: str = "text-embedding-3-small"
    dimension: int = 1536
    max_input_tokens: int = 8192
    batch_size: int = 32
    api_key: str | None = None
    base_url: str | None = None


class BaseEmbedder(ABC):
    provider_id: str = ""
    model: str = ""
    dimension: int = 0
    max_input_tokens: int = 0
    is_local: bool = False

    def __init__(self, config: EmbeddingConfig | None = None) -> None:
        self.config = config or EmbeddingConfig()

    @abstractmethod
    async def embed(self, text: str) -> EmbeddingResult:
        ...

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        return [await self.embed(t) for t in texts]

    @abstractmethod
    async def embed_query(self, query: str) -> EmbeddingResult:
        ...

    async def count_tokens(self, text: str) -> int:
        return len(text) // 4
