from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ai.evaluation.metrics import (
    BaseMetric,
    CitationAccuracyMetric,
    CompletenessMetric,
    CoverageMetric,
    GapQualityMetric,
    GroundednessMetric,
    HallucinationMetric,
    MetricResult,
    NoveltySupportMetric,
    TraceabilityMetric,
)


@dataclass
class EvaluationReport:
    workflow_id: str = ""
    phase: str = ""
    metrics: list[MetricResult] = field(default_factory=list)
    overall_score: float = 0.0
    passed: bool = False
    artifact_id: str = ""


class EvaluationEngine:
    def __init__(self) -> None:
        self._metrics: dict[str, list[BaseMetric]] = {
            "research": [CoverageMetric()],
            "analysis": [GapQualityMetric()],
            "ideas": [NoveltySupportMetric()],
            "draft": [
                CitationAccuracyMetric(),
                GroundednessMetric(),
                HallucinationMetric(),
                TraceabilityMetric(),
                CompletenessMetric(),
            ],
            "review": [],
        }

    def register_metric(self, phase: str, metric: BaseMetric) -> None:
        if phase not in self._metrics:
            self._metrics[phase] = []
        self._metrics[phase].append(metric)

    async def evaluate(
        self, phase: str, artifact: Any, **kwargs: Any
    ) -> EvaluationReport:
        phase_metrics = self._metrics.get(phase, [])
        results: list[MetricResult] = []

        for metric in phase_metrics:
            result = await metric.evaluate(**kwargs)
            results.append(result)

        overall = sum(r.score for r in results) / max(len(results), 1)

        return EvaluationReport(
            phase=phase,
            metrics=results,
            overall_score=overall,
            passed=all(r.passed for r in results),
        )

    def list_metrics(self, phase: str) -> list[str]:
        return [m.__class__.__name__ for m in self._metrics.get(phase, [])]
