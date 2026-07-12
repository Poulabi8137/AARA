from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings


class RAGSettings(BaseSettings):
    # Retrieval
    retrieval_top_k: int = 10
    retrieval_semantic_top_k: int = 10
    retrieval_keyword_top_k: int = 10
    retrieval_hybrid_weight: float = 0.7
    retrieval_min_confidence: float = 0.3
    retrieval_similarity_threshold: float = 0.7
    retrieval_rerank_enabled: bool = True
    retrieval_rerank_top_k: int = 5
    retrieval_platform_top_k: int = 5

    # Collection routing
    routing_default_strategy: str = "intent_based"
    routing_keyword_boost: bool = True

    # Ranking weights
    ranking_semantic_weight: float = 0.5
    ranking_source_weight: float = 0.2
    ranking_freshness_weight: float = 0.15
    ranking_confidence_weight: float = 0.15
    ranking_freshness_decay_days: int = 365

    # Citation retrieval
    citation_max_per_query: int = 5
    citation_score_threshold: float = 0.5

    # Context
    context_max_tokens: int = 4096
    context_chunk_max_tokens: int = 512
    context_deduplication_enabled: bool = True
    context_deduplication_similarity: float = 0.85

    # Response
    response_max_tokens: int = 2048
    response_temperature: float = 0.3
    response_include_evidence: bool = True
    response_include_sources: bool = True
    response_include_confidence: bool = True

    # LLM provider
    provider_model: str = "gpt-4o"
    provider_temperature: float = 0.3
    provider_max_tokens: int = 4096
    provider_timeout_seconds: int = 120

    class Config:
        env_prefix = "rag_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_rag_settings() -> RAGSettings:
    return RAGSettings()
