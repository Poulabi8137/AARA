from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ai.evaluation.metrics import MetricResult


@dataclass
class AggregatedScore:
    overall: float = 0.0
    min_score: float = 0.0
    max_score: float = 0.0
    median_score: float = 0.0
    passed_count: int = 0
    total_count: int = 0
    details: dict[str, Any] = field(default_factory=dict)


class QualityAggregator:
    def aggregate(self, results: list[MetricResult]) -> AggregatedScore:
        if not results:
            return AggregatedScore()

        scores = [r.score for r in results]
        sorted_scores = sorted(scores)
        n = len(sorted_scores)

        return AggregatedScore(
            overall=sum(scores) / n,
            min_score=min(scores),
            max_score=max(scores),
            median_score=sorted_scores[n // 2] if n % 2
            else (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2,
            passed_count=sum(1 for r in results if r.passed),
            total_count=n,
            details={r.name: {"score": r.score, "passed": r.passed} for r in results},
        )

    def weighted_aggregate(
        self, results: list[MetricResult], weights: dict[str, float]
    ) -> AggregatedScore:
        if not results:
            return AggregatedScore()

        total_weight = 0.0
        weighted_sum = 0.0
        for r in results:
            w = weights.get(r.name, 1.0)
            weighted_sum += r.score * w
            total_weight += w

        scores = [r.score for r in results]
        sorted_scores = sorted(scores)
        n = len(sorted_scores)

        return AggregatedScore(
            overall=weighted_sum / max(total_weight, 0.001),
            min_score=min(scores),
            max_score=max(scores),
            median_score=sorted_scores[n // 2] if n % 2
            else (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2,
            passed_count=sum(1 for r in results if r.passed),
            total_count=n,
            details={
                r.name: {"score": r.score, "passed": r.passed, "weight": weights.get(r.name, 1.0)}
                for r in results
            },
        )
