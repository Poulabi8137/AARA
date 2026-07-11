from __future__ import annotations

import hashlib

from app.ai.embedding.interface import EmbeddingResult


class EmbeddingCache:
    def __init__(self, max_size: int = 10000) -> None:
        self._cache: dict[str, EmbeddingResult] = {}
        self._max_size = max_size

    def _make_key(self, text: str, model: str) -> str:
        return hashlib.sha256(f"{model}:{text}".encode()).hexdigest()

    def get(self, text: str, model: str) -> EmbeddingResult | None:
        key = self._make_key(text, model)
        return self._cache.get(key)

    def set(self, text: str, model: str, result: EmbeddingResult) -> None:
        if len(self._cache) >= self._max_size:
            self._evict()
        key = self._make_key(text, model)
        self._cache[key] = result

    def get_batch(self, texts: list[str], model: str) -> dict[int, EmbeddingResult]:
        results: dict[int, EmbeddingResult] = {}
        for i, text in enumerate(texts):
            cached = self.get(text, model)
            if cached:
                results[i] = cached
        return results

    def clear(self) -> None:
        self._cache.clear()

    def size(self) -> int:
        return len(self._cache)

    def _evict(self) -> None:
        keys = list(self._cache.keys())
        for k in keys[: len(keys) // 4]:
            del self._cache[k]
