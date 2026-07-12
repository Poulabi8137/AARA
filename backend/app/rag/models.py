from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SearchIntent(str, Enum):
    FACTUAL = "factual"
    EXPLORATORY = "exploratory"
    COMPARATIVE = "comparative"
    METHODOLOGICAL = "methodological"
    CRITICAL = "critical"
    SUMMARIZATION = "summarization"


class RetrievalStrategy(str, Enum):
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class SourceType(str, Enum):
    MEMORY_SESSION = "session_memory"
    MEMORY_LONG_TERM = "long_term_memory"
    MEMORY_PAPER = "paper_memory"
    MEMORY_PROJECT = "project_memory"
    CHROMA_PAPER = "research_papers"
    CHROMA_WEB = "web_search_results"
    CHROMA_CITATION = "citations"
    CHROMA_REPORT = "generated_reports"
    CHROMA_KNOWLEDGE = "knowledge_base"


class RoutingStrategy(str, Enum):
    INTENT_BASED = "intent_based"
    KEYWORD_BASED = "keyword_based"
    ALL_COLLECTIONS = "all_collections"


_MEMORY_COLLECTIONS: list[SourceType] = [
    SourceType.MEMORY_SESSION,
    SourceType.MEMORY_LONG_TERM,
    SourceType.MEMORY_PAPER,
    SourceType.MEMORY_PROJECT,
]

_PLATFORM_COLLECTIONS: list[SourceType] = [
    SourceType.CHROMA_PAPER,
    SourceType.CHROMA_WEB,
    SourceType.CHROMA_CITATION,
    SourceType.CHROMA_REPORT,
    SourceType.CHROMA_KNOWLEDGE,
]

ALL_COLLECTIONS: list[SourceType] = _MEMORY_COLLECTIONS + _PLATFORM_COLLECTIONS


@dataclass
class CollectionRoute:
    collections: list[SourceType]
    strategy: RoutingStrategy
    label: str = ""


@dataclass
class CollectionAnalytics:
    collection: SourceType
    hits: int = 0
    latency_ms: float = 0.0
    search_strategy: str = "semantic"


@dataclass
class ProcessedQuery:
    raw: str
    normalized: str
    rewritten: str | None = None
    intent: SearchIntent = SearchIntent.FACTUAL
    keywords: list[str] = field(default_factory=list)
    metadata_filters: dict[str, Any] = field(default_factory=dict)
    search_strategies: list[RetrievalStrategy] = field(
        default_factory=lambda: [RetrievalStrategy.HYBRID]
    )
    user_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    confidence_threshold: float = 0.0
    top_k: int = 10


@dataclass
class RetrievedEvidence:
    content: str
    source_type: SourceType
    source_id: str
    score: float
    rank: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    provenance: str | None = None
    original_collections: list[SourceType] = field(default_factory=list)
    freshness_score: float = 1.0
    source_priority: int = 5


@dataclass
class RetrievalOutput:
    query: ProcessedQuery
    evidence: list[RetrievedEvidence]
    total_candidates: int = 0
    semantic_results: int = 0
    keyword_results: int = 0
    duplicates_removed: int = 0
    confidence: float = 0.0
    duration_seconds: float = 0.0
    collections_searched: list[CollectionAnalytics] = field(default_factory=list)
    collection_stats: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextChunk:
    content: str
    source_type: SourceType
    source_id: str
    score: float
    rank: int
    citation: str | None = None
    token_count: int = 0


@dataclass
class RAGContext:
    chunks: list[ContextChunk]
    total_tokens: int = 0
    budget_tokens: int = 0
    truncated: bool = False
    sources: list[str] = field(default_factory=list)


@dataclass
class RAGResponse:
    answer: str
    context: RAGContext
    evidence: list[RetrievedEvidence]
    confidence: float
    model: str
    query: ProcessedQuery
    retrieval_stats: dict[str, Any] = field(default_factory=dict)
    processing_metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
