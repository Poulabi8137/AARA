from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricResult:
    name: str = ""
    score: float = 0.0
    threshold: float = 0.0
    passed: bool = False
    details: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseMetric(ABC):
    @abstractmethod
    async def evaluate(self, **kwargs: Any) -> MetricResult:
        ...


class CitationAccuracyMetric(BaseMetric):
    async def evaluate(
        self, citations: list[dict[str, Any]] | None = None, **kwargs: Any
    ) -> MetricResult:
        citations = citations or kwargs.get("citations", [])
        total = len(citations)
        valid = sum(1 for c in citations if c.get("verified", False))
        accuracy = valid / max(total, 1)
        return MetricResult(
            name="citation_accuracy",
            score=accuracy,
            threshold=0.9,
            passed=accuracy >= 0.9,
            details=f"{valid}/{total} citations verified",
        )


class GroundednessMetric(BaseMetric):
    async def evaluate(
        self, claims: list[dict[str, Any]] | None = None, **kwargs: Any
    ) -> MetricResult:
        claims = claims or kwargs.get("claims", [])
        total = len(claims)
        supported = sum(1 for c in claims if c.get("has_citation", False))
        groundedness = supported / max(total, 1)
        return MetricResult(
            name="groundedness",
            score=groundedness,
            threshold=0.8,
            passed=groundedness >= 0.8,
            details=f"{supported}/{total} claims have citations",
        )


class HallucinationMetric(BaseMetric):
    SAMPLE_SIZE = 5

    async def evaluate(
        self, sampled_claims: list[dict[str, Any]] | None = None, **kwargs: Any
    ) -> MetricResult:
        sampled = sampled_claims or kwargs.get("sampled_claims", [])
        hallucinations = sum(1 for c in sampled if c.get("is_hallucination", False))
        rate = hallucinations / max(len(sampled), 1)
        return MetricResult(
            name="hallucination_rate",
            score=1.0 - rate,
            threshold=0.95,
            passed=rate <= 0.05,
            details=f"{hallucinations}/{len(sampled)} claims potentially hallucinated",
        )


class CoverageMetric(BaseMetric):
    async def evaluate(self, coverage_score: float | None = None, **kwargs: Any) -> MetricResult:
        score = coverage_score if coverage_score is not None else kwargs.get("coverage_score", 0.0)
        return MetricResult(
            name="coverage",
            score=score,
            threshold=0.6,
            passed=score >= 0.6,
            details=f"Coverage: {score:.2f}",
            metadata={"missing_topics": kwargs.get("missing_topics", [])},
        )


class GapQualityMetric(BaseMetric):
    async def evaluate(self, **kwargs: Any) -> MetricResult:
        specificity = kwargs.get("specificity", 0.0)
        actionability = kwargs.get("actionability", 0.0)
        evidence_support = kwargs.get("evidence_support", 0.0)
        composite = (specificity + actionability + evidence_support) / 3
        return MetricResult(
            name="gap_quality",
            score=composite,
            threshold=0.5,
            passed=composite >= 0.5,
            details=f"S={specificity:.2f} A={actionability:.2f} E={evidence_support:.2f}",
        )


class NoveltySupportMetric(BaseMetric):
    async def evaluate(self, overlap_score: float | None = None, **kwargs: Any) -> MetricResult:
        overlap = overlap_score if overlap_score is not None else kwargs.get("overlap_score", 0.0)
        novelty = 1.0 - overlap
        return MetricResult(
            name="novelty_support",
            score=novelty,
            threshold=0.4,
            passed=overlap <= 0.6,
            details=f"Overlap: {overlap:.2f}, Novelty: {novelty:.2f}",
        )


class TraceabilityMetric(BaseMetric):
    async def evaluate(
        self, traced: int | None = None, total: int | None = None, **kwargs: Any
    ) -> MetricResult:
        traced = traced or kwargs.get("traced", 0)
        total = total or kwargs.get("total_citations", 0)
        traceability = traced / max(total, 1)
        return MetricResult(
            name="traceability",
            score=traceability,
            threshold=0.95,
            passed=traceability >= 0.95,
            details=f"{traced}/{total} citations traceable",
        )


class CompletenessMetric(BaseMetric):
    REQUIRED_SECTIONS = {"abstract", "introduction", "related_work", "conclusion"}
    MIN_WORDS = 100

    async def evaluate(
        self, sections: list[dict[str, Any]] | None = None, **kwargs: Any
    ) -> MetricResult:
        sections = sections or kwargs.get("sections", [])
        present = set(s.get("name", "") for s in sections)
        missing = self.REQUIRED_SECTIONS - present
        short = [
            s.get("name", "") for s in sections
            if len(s.get("content", "").split()) < self.MIN_WORDS
        ]
        total_sections = max(len(self.REQUIRED_SECTIONS) + len(sections), 1)
        completeness = 1.0 - (len(missing) + len(short)) / total_sections
        return MetricResult(
            name="completeness",
            score=max(0.0, completeness),
            threshold=0.8,
            passed=len(missing) == 0 and len(short) == 0,
            details=f"Missing: {missing}, Short sections: {short}",
        )
