from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger
from app.vectorstore.embeddings import (
    EmbeddingProvider,
    MiniLMEmbeddingProvider,
    OpenAIEmbeddingProvider,
)

logger = get_logger("vectorstore.provider_factory")
settings = get_settings()


_PROVIDER_REGISTRY: dict[str, type[EmbeddingProvider]] = {
    "minilm": MiniLMEmbeddingProvider,
    "openai": OpenAIEmbeddingProvider,
}


def register_provider(name: str, provider_cls: type[EmbeddingProvider]) -> None:
    _PROVIDER_REGISTRY[name] = provider_cls
    logger.info(
        "registered embedding provider",
        extra={"name": name, "cls": provider_cls.__name__},
    )


def get_embedding_provider(
    provider_name: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> EmbeddingProvider:
    name = (provider_name or settings.embedding_provider or "minilm").lower()

    cls = _PROVIDER_REGISTRY.get(name)
    if cls is None:
        logger.warning(
            "unknown embedding provider, falling back to minilm",
            extra={"requested": name, "available": list(_PROVIDER_REGISTRY.keys())},
        )
        cls = MiniLMEmbeddingProvider

    if cls is OpenAIEmbeddingProvider:
        key = api_key or settings.openai_api_key or ""
        return cls(api_key=key, model=model)

    logger.info(
        "created embedding provider", extra={"provider": name, "cls": cls.__name__}
    )
    return cls()


def list_providers() -> list[str]:
    return list(_PROVIDER_REGISTRY.keys())
