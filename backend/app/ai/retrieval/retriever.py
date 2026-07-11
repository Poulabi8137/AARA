from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrieverResult:
    content: str
    score: float
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseRetriever(ABC):
    @abstractmethod
    async def retrieve(
        self, query: str, limit: int = 10, **kwargs: Any
    ) -> list[RetrieverResult]:
        ...
