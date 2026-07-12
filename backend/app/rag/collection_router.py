from __future__ import annotations

import re
from app.core.logging import get_logger
from app.rag.config import get_rag_settings
from app.rag.models import (
    ALL_COLLECTIONS,
    CollectionRoute,
    ProcessedQuery,
    RoutingStrategy,
    SearchIntent,
    SourceType,
)

logger = get_logger("rag.collection_router")
settings = get_rag_settings()

_INTENT_ROUTES: dict[SearchIntent, list[SourceType]] = {
    SearchIntent.FACTUAL: [
        SourceType.CHROMA_PAPER,
        SourceType.CHROMA_CITATION,
        SourceType.CHROMA_KNOWLEDGE,
        SourceType.MEMORY_LONG_TERM,
        SourceType.MEMORY_PAPER,
    ],
    SearchIntent.EXPLORATORY: [
        SourceType.CHROMA_PAPER,
        SourceType.CHROMA_WEB,
        SourceType.CHROMA_KNOWLEDGE,
        SourceType.CHROMA_REPORT,
        SourceType.MEMORY_LONG_TERM,
    ],
    SearchIntent.COMPARATIVE: [
        SourceType.CHROMA_PAPER,
        SourceType.CHROMA_CITATION,
        SourceType.MEMORY_PAPER,
        SourceType.MEMORY_LONG_TERM,
    ],
    SearchIntent.METHODOLOGICAL: [
        SourceType.CHROMA_PAPER,
        SourceType.CHROMA_KNOWLEDGE,
        SourceType.MEMORY_PAPER,
        SourceType.MEMORY_PROJECT,
    ],
    SearchIntent.CRITICAL: [
        SourceType.CHROMA_PAPER,
        SourceType.CHROMA_CITATION,
        SourceType.MEMORY_PAPER,
        SourceType.MEMORY_SESSION,
    ],
    SearchIntent.SUMMARIZATION: [
        SourceType.CHROMA_REPORT,
        SourceType.CHROMA_PAPER,
        SourceType.MEMORY_LONG_TERM,
        SourceType.MEMORY_PROJECT,
    ],
}

_KEYWORD_ROUTES: list[tuple[re.Pattern, list[SourceType]]] = [
    (
        re.compile(r"\b(literature|survey|review|paper|publication)\b", re.IGNORECASE),
        [
            SourceType.CHROMA_PAPER,
            SourceType.CHROMA_CITATION,
            SourceType.CHROMA_KNOWLEDGE,
            SourceType.MEMORY_PAPER,
        ],
    ),
    (
        re.compile(r"\b(experiment|result|finding|observation)\b", re.IGNORECASE),
        [
            SourceType.MEMORY_PROJECT,
            SourceType.CHROMA_REPORT,
            SourceType.MEMORY_LONG_TERM,
            SourceType.MEMORY_SESSION,
        ],
    ),
    (
        re.compile(
            r"\b(method|approach|technique|algorithm|framework)\b", re.IGNORECASE
        ),
        [
            SourceType.MEMORY_PAPER,
            SourceType.CHROMA_PAPER,
            SourceType.CHROMA_KNOWLEDGE,
            SourceType.MEMORY_PROJECT,
        ],
    ),
    (
        re.compile(r"\b(cite|citation|reference|bibliography)\b", re.IGNORECASE),
        [
            SourceType.CHROMA_CITATION,
            SourceType.CHROMA_PAPER,
            SourceType.MEMORY_PAPER,
        ],
    ),
    (
        re.compile(r"\b(web|news|blog|article|online)\b", re.IGNORECASE),
        [
            SourceType.CHROMA_WEB,
            SourceType.CHROMA_KNOWLEDGE,
        ],
    ),
    (
        re.compile(r"\b(report|summary|generated|output)\b", re.IGNORECASE),
        [
            SourceType.CHROMA_REPORT,
            SourceType.MEMORY_LONG_TERM,
        ],
    ),
]


class CollectionRouter:
    def route(
        self,
        query: ProcessedQuery,
        strategy: RoutingStrategy | None = None,
    ) -> CollectionRoute:
        strategy = strategy or RoutingStrategy.INTENT_BASED

        if strategy == RoutingStrategy.ALL_COLLECTIONS:
            return CollectionRoute(
                collections=list(ALL_COLLECTIONS),
                strategy=strategy,
                label="all_collections",
            )

        if strategy == RoutingStrategy.KEYWORD_BASED:
            matches: list[SourceType] = []
            seen: set[SourceType] = set()
            for pattern, cols in _KEYWORD_ROUTES:
                if pattern.search(query.normalized):
                    for c in cols:
                        if c not in seen:
                            seen.add(c)
                            matches.append(c)
            if matches:
                return CollectionRoute(
                    collections=matches,
                    strategy=strategy,
                    label="keyword_matched",
                )

        intent_cols = _INTENT_ROUTES.get(query.intent, list(ALL_COLLECTIONS))
        return CollectionRoute(
            collections=intent_cols,
            strategy=RoutingStrategy.INTENT_BASED,
            label=f"intent:{query.intent.value}",
        )

    def memory_collections(self, route: CollectionRoute) -> list[SourceType]:
        return [
            c
            for c in route.collections
            if c
            in {
                SourceType.MEMORY_SESSION,
                SourceType.MEMORY_LONG_TERM,
                SourceType.MEMORY_PAPER,
                SourceType.MEMORY_PROJECT,
            }
        ]

    def platform_collections(self, route: CollectionRoute) -> list[SourceType]:
        return [
            c
            for c in route.collections
            if c
            in {
                SourceType.CHROMA_PAPER,
                SourceType.CHROMA_WEB,
                SourceType.CHROMA_CITATION,
                SourceType.CHROMA_REPORT,
                SourceType.CHROMA_KNOWLEDGE,
            }
        ]
