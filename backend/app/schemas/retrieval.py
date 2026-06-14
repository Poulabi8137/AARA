from __future__ import annotations

from pydantic import BaseModel, Field


class RetrievedChunkSchema(BaseModel):
    query: str
    source: str
    content: str
    relevance_score: float = Field(default=0.0, ge=0.0, le=100.0)
    collection: str
    metadata: dict = Field(default_factory=dict)
    retrieval_reason: str = ""
    chunk_id: str = ""


class RetrievalBundle(BaseModel):
    subtopic: str
    title: str
    evidence: list[RetrievedChunkSchema] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=100.0)
    coverage: bool = False


class RetrievalDebugInfo(BaseModel):
    total_collections_searched: int = 0
    collection_hit_counts: dict[str, int] = Field(default_factory=dict)
    documents_before_dedup: int = 0
    documents_after_dedup: int = 0
    duplicates_removed: int = 0
    search_queries_used: list[str] = Field(default_factory=list)
    ranking_distribution: dict[str, float] = Field(default_factory=dict)
    coverage_scores: dict[str, bool] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class RetrievalMetrics(BaseModel):
    latency_seconds: float = 0.0
    total_collections_searched: int = 0
    collection_hit_counts: dict[str, int] = Field(default_factory=dict)
    documents_before_dedup: int = 0
    documents_after_dedup: int = 0
    duplicates_removed: int = 0
    average_relevance: float = 0.0
    top_relevance: float = 0.0
    coverage_ratio: float = 0.0
    bundles: int = 0
    used_fallback: bool = False
    errors: list[str] = Field(default_factory=list)
