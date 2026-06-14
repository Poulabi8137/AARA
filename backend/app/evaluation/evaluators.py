from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.evaluation.metrics import METRIC_REGISTRY, METRIC_WEIGHTS
from app.evaluation.scorecard import generate_scorecard

logger = get_logger("evaluation.evaluators")


class WorkflowEvaluator:
    """Evaluates a complete workflow execution and persists results.

    Usage:
        evaluator = WorkflowEvaluator()
        result = await evaluator.evaluate(state)
    """

    def __init__(self):
        self._metrics = METRIC_REGISTRY
        self._weights = METRIC_WEIGHTS

    async def evaluate(
        self,
        state: dict[str, Any],
        execution_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Run full evaluation on a workflow state.

        Args:
            state: ResearchState dict from workflow execution.
            execution_id: Optional execution UUID for persistence.
            project_id: Optional project UUID for persistence.

        Returns:
            Evaluation result dict with scorecard, metrics list, and metadata.
        """
        start = datetime.now(timezone.utc)

        scorecard = generate_scorecard(state)

        metrics_list = []
        for name, score in scorecard.get("scores", {}).items():
            metrics_list.append({
                "metric_name": name,
                "score": round(score, 2),
                "weight": self._weights.get(name, 1.0),
            })

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()

        return {
            "execution_id": execution_id,
            "project_id": project_id,
            "query": state.get("query", ""),
            "scorecard": scorecard,
            "metrics": metrics_list,
            "evaluation_latency": elapsed,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    def compute_trend(
        self,
        evaluations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compute score trends across multiple evaluations.

        Args:
            evaluations: List of evaluation result dicts.

        Returns:
            dict with averages, min/max, and per-metric trends.
        """
        if not evaluations:
            return {
                "average_quality": 0.0,
                "min_quality": 0.0,
                "max_quality": 0.0,
                "trend_direction": "unknown",
                "metric_averages": {},
                "evaluation_count": 0,
            }

        scores = []
        metric_scores: dict[str, list[float]] = {}

        for ev in evaluations:
            sc = ev.get("scorecard", {})
            composite = sc.get("composite", 0)
            scores.append(composite)

            for name, val in sc.get("scores", {}).items():
                metric_scores.setdefault(name, []).append(val)

        metric_averages = {
            name: round(sum(vals) / len(vals), 2)
            for name, vals in metric_scores.items()
        }

        avg_q = round(sum(scores) / len(scores), 2)
        min_q = round(min(scores), 2)
        max_q = round(max(scores), 2)

        if len(scores) >= 2:
            first_half = sum(scores[: len(scores) // 2]) / (len(scores) // 2)
            second_half = sum(scores[len(scores) // 2 :]) / (len(scores) - len(scores) // 2)
            if second_half > first_half + 2:
                direction = "improving"
            elif second_half < first_half - 2:
                direction = "declining"
            else:
                direction = "stable"
        else:
            direction = "insufficient_data"

        return {
            "average_quality": avg_q,
            "min_quality": min_q,
            "max_quality": max_q,
            "trend_direction": direction,
            "metric_averages": metric_averages,
            "evaluation_count": len(evaluations),
        }

    def compute_metric_distributions(
        self,
        evaluations: list[dict[str, Any]],
    ) -> dict[str, dict[str, float]]:
        """Compute distribution statistics per metric.

        Returns dict of metric_name -> {min, max, avg, median, p25, p75, stddev}.
        """
        import statistics

        metric_values: dict[str, list[float]] = {}
        for ev in evaluations:
            sc = ev.get("scorecard", {})
            for name, val in sc.get("scores", {}).items():
                metric_values.setdefault(name, []).append(val)

        distributions = {}
        for name, vals in metric_values.items():
            if not vals:
                continue
            sorted_vals = sorted(vals)
            n = len(sorted_vals)
            distributions[name] = {
                "min": round(min(vals), 2),
                "max": round(max(vals), 2),
                "avg": round(sum(vals) / n, 2),
                "median": round(
                    sorted_vals[n // 2] if n % 2 == 1
                    else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2,
                    2,
                ),
                "p25": round(sorted_vals[int(n * 0.25)], 2),
                "p75": round(sorted_vals[int(n * 0.75)], 2),
                "stddev": round(statistics.stdev(vals), 2) if n >= 2 else 0.0,
            }

        return distributions
