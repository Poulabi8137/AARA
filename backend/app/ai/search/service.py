from __future__ import annotations

import re
import time
from collections.abc import Sequence

from app.ai.search.models import PaperMetadata, ProviderResult
from app.ai.search.protocol import AcademicSearchProvider


class AcademicSearchService:
    def __init__(self, providers: Sequence[AcademicSearchProvider]) -> None:
        self._providers = list(providers)
        self._last_provider_results: list[ProviderResult] = []

    @property
    def last_provider_results(self) -> list[ProviderResult]:
        return list(self._last_provider_results)

    async def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[PaperMetadata]:
        import asyncio

        async def _run(
            provider: AcademicSearchProvider,
            q: str,
            provider_limit: int,
        ) -> tuple[list[PaperMetadata], float, ProviderResult]:
            start = time.monotonic()
            provider_id = getattr(provider, "provider_id", "unknown")
            try:
                results = await provider.search(query=q, limit=provider_limit * 2)
                elapsed = time.monotonic() - start
                result = ProviderResult(
                    provider=provider_id,
                    status="success",
                    latency=elapsed,
                    paper_count=len(results),
                )
                return results, elapsed, result
            except Exception as e:
                elapsed = time.monotonic() - start
                result = ProviderResult(
                    provider=provider_id,
                    status="error",
                    latency=elapsed,
                    paper_count=0,
                    error_message=str(e),
                )
                return [], elapsed, result

        raw_results: list[list[PaperMetadata]] = []
        self._last_provider_results = []
        provider_coros = [_run(p, query, limit) for p in self._providers]
        provider_results = await asyncio.gather(
            *provider_coros,
            return_exceptions=True,
        )

        for r in provider_results:
            if isinstance(r, tuple):
                papers, _elapsed, result = r
                raw_results.extend(papers)
                self._last_provider_results.append(result)

        merged = self._deduplicate(raw_results)
        ranked = self._rank(merged)
        return ranked[:limit]

    def _deduplicate(
        self,
        papers: list[PaperMetadata],
    ) -> list[PaperMetadata]:
        seen_dois: set[str] = set()
        seen_titles: set[str] = set()
        unique: list[PaperMetadata] = []

        for p in papers:
            key = self._dedup_key(p)
            if key in seen_dois:
                continue
            seen_dois.add(key)

            normalized = self._normalize_title(p.title)
            if normalized in seen_titles:
                existing = next(
                    (u for u in unique if self._normalize_title(u.title) == normalized),
                    None,
                )
                if existing and self._should_replace(existing, p):
                    unique.remove(existing)
                    unique.append(p)
                continue

            if self._has_similar_title(normalized, seen_titles):
                continue

            seen_titles.add(normalized)
            unique.append(p)

        return unique

    def _dedup_key(self, paper: PaperMetadata) -> str:
        if paper.doi:
            return f"doi:{paper.doi.lower().strip()}"
        normalized = self._normalize_title(paper.title)
        return f"title:{normalized}"

    def _normalize_title(self, title: str) -> str:
        normalized = title.lower().strip()
        normalized = re.sub(r"[^\w\s]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _has_similar_title(self, candidate: str, seen: set[str]) -> bool:
        candidate_words = set(candidate.split())
        if not candidate_words:
            return False
        for existing in seen:
            existing_words = set(existing.split())
            intersection = candidate_words.intersection(existing_words)
            union = candidate_words.union(existing_words)
            jaccard = len(intersection) / len(union) if union else 0.0
            if jaccard > 0.6:
                return True
        return False

    def _should_replace(
        self,
        existing: PaperMetadata,
        candidate: PaperMetadata,
    ) -> bool:
        existing_score = (
            (existing.citation_count or 0) * 2
            + (1 if existing.abstract else 0)
            + (1 if existing.doi else 0)
            + (1 if existing.pdf_url else 0)
        )
        candidate_score = (
            (candidate.citation_count or 0) * 2
            + (1 if candidate.abstract else 0)
            + (1 if candidate.doi else 0)
            + (1 if candidate.pdf_url else 0)
        )
        return candidate_score > existing_score

    def _rank(self, papers: list[PaperMetadata]) -> list[PaperMetadata]:
        def _score(p: PaperMetadata) -> float:
            citation_score = min((p.citation_count or 0) / 1000.0, 1.0) * 0.4
            year_score = 0.0
            if p.year:
                age = 2026 - p.year
                year_score = max(0.0, 1.0 - age / 30.0) * 0.3
            abstract_score = 0.2 if p.abstract else 0.0
            doi_score = 0.1 if p.doi else 0.0
            return citation_score + year_score + abstract_score + doi_score

        return sorted(papers, key=_score, reverse=True)
