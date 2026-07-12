from __future__ import annotations

import time

from app.core.logging import get_logger
from app.experiments.config import get_experiment_settings
from app.experiments.models import (
    EvaluationMetric,
    ExpectedOutcome,
    ExperimentPhase,
)
from app.methodology.models import MethodologyResult
from app.rag.llm import RAGLLMProvider

logger = get_logger("experiments.evaluation")
settings = get_experiment_settings()

_EVALUATION_SYSTEM: str = (
    "You are an experiment evaluation planning assistant. "
    "Generate comprehensive evaluation plans.\n\n"
    "For each evaluation metric:\n"
    "- Name\n"
    "- Description\n"
    "- Expected value (numeric threshold)\n"
    "- Threshold (minimum acceptable)\n"
    "- Direction (higher_is_better|lower_is_better)\n"
    "- Statistical test (e.g., paired t-test, Wilcoxon)\n\n"
    "For each expected outcome:\n"
    "- Outcome description\n"
    "- Category (primary|secondary|exploratory)\n"
    "- Likelihood (0.0-1.0)\n"
    "- Impact (high|medium|low)\n"
    "- Supporting evidence\n\n"
    "Include:\n"
    "- Statistical tests\n"
    "- Success criteria\n"
    "- Reproducibility checklist\n"
    "- Error analysis approach\n"
    "- Robustness testing\n\n"
    "Format metrics:\n"
    "Metric: <name>\n"
    "Description: <description>\n"
    "Expected: <value>\n"
    "Threshold: <value>\n"
    "Direction: higher_is_better|lower_is_better\n"
    "Statistical Test: <test>\n\n"
    "Format outcomes:\n"
    "Outcome: <description>\n"
    "Category: primary|secondary|exploratory\n"
    "Likelihood: 0.X\n"
    "Impact: high|medium|low\n"
    "Evidence: <comma-separated>"
)

_EVALUATION_USER: str = (
    "Research Query: {query}\n"
    "Methods: {methods}\n"
    "Number of Phases: {num_phases}\n\n"
    "Generate evaluation metrics and expected outcomes."
)


class EvaluationPlanner:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def plan(
        self,
        query: str,
        methodology_result: MethodologyResult,
        phases: list[ExperimentPhase],
    ) -> tuple[list[EvaluationMetric], list[ExpectedOutcome]]:
        start = time.monotonic()

        metrics = self._default_metrics(methodology_result)
        outcomes = self._default_outcomes()

        if self._llm and settings.enable_llm:
            llm_metrics, llm_outcomes = await self._llm_plan(
                query, methodology_result, phases
            )
            metrics = self._dedup(metrics, llm_metrics)
            outcomes = self._dedup(outcomes, llm_outcomes)

        logger.info(
            "evaluation planning complete",
            extra={
                "metrics": len(metrics),
                "outcomes": len(outcomes),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )

        return metrics, outcomes

    def _default_metrics(
        self,
        mr: MethodologyResult,
    ) -> list[EvaluationMetric]:
        metrics: list[EvaluationMetric] = [
            EvaluationMetric(
                name="accuracy",
                description="Overall prediction accuracy",
                expected_value=0.85,
                threshold=0.5,
                direction="higher_is_better",
                statistical_test="paired_t_test",
            ),
            EvaluationMetric(
                name="f1_score",
                description="Harmonic mean of precision and recall",
                expected_value=0.80,
                threshold=0.5,
                direction="higher_is_better",
                statistical_test="wilcoxon",
            ),
        ]

        if mr.methods:
            first = mr.methods[0]
            if first.confidence > 0.5:
                metrics.append(
                    EvaluationMetric(
                        name="comparison_improvement",
                        description=f"Improvement over {first.method} baseline",
                        expected_value=first.confidence,
                        threshold=0.0,
                        direction="higher_is_better",
                        statistical_test="paired_t_test",
                    )
                )

        return metrics

    def _default_outcomes(self) -> list[ExpectedOutcome]:
        return [
            ExpectedOutcome(
                outcome="Model achieves competitive performance on benchmark datasets",
                category="primary",
                likelihood=0.6,
                impact="high",
                evidence=["Literature survey", "Preliminary experiments"],
            ),
            ExpectedOutcome(
                outcome="Proposed method outperforms baselines",
                category="primary",
                likelihood=0.5,
                impact="high",
                evidence=["Theoretical analysis", "Related work"],
            ),
            ExpectedOutcome(
                outcome="Ablation study reveals key component contributions",
                category="secondary",
                likelihood=0.7,
                impact="medium",
                evidence=["Standard practice in literature"],
            ),
        ]

    async def _llm_plan(
        self,
        query: str,
        mr: MethodologyResult,
        phases: list[ExperimentPhase],
    ) -> tuple[list[EvaluationMetric], list[ExpectedOutcome]]:
        try:
            methods_text = (
                ", ".join(m.method for m in mr.methods[:5]) if mr.methods else "none"
            )
            content = await self._llm.generate(
                prompt=_EVALUATION_USER.format(
                    query=query,
                    methods=methods_text,
                    num_phases=len(phases),
                ),
                system_prompt=_EVALUATION_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            return self._parse_content(content)
        except Exception as exc:
            logger.warning("LLM evaluation planning failed", extra={"error": str(exc)})
            return [], []

    def _parse_content(
        self,
        content: str,
    ) -> tuple[list[EvaluationMetric], list[ExpectedOutcome]]:
        metrics: list[EvaluationMetric] = []
        outcomes: list[ExpectedOutcome] = []
        current_metric: dict = {}
        current_outcome: dict = {}
        in_metric = False
        in_outcome = False

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            low = line.lower()

            if low.startswith("metric:"):
                if current_metric.get("name"):
                    metrics.append(self._build_metric(current_metric))
                current_metric = {"name": line.split(":", 1)[1].strip()}
                current_outcome = {}
                in_metric = True
                in_outcome = False
            elif low.startswith("outcome:"):
                if current_outcome.get("outcome"):
                    outcomes.append(self._build_outcome(current_outcome))
                current_outcome = {"outcome": line.split(":", 1)[1].strip()}
                current_metric = {}
                in_metric = False
                in_outcome = True
            elif in_metric:
                if low.startswith("description:"):
                    current_metric["description"] = line.split(":", 1)[1].strip()
                elif low.startswith("expected:"):
                    try:
                        current_metric["expected"] = float(line.split(":")[1].strip())
                    except (ValueError, TypeError):
                        current_metric["expected"] = 0.5
                elif low.startswith("threshold:"):
                    try:
                        current_metric["threshold"] = float(line.split(":")[1].strip())
                    except (ValueError, TypeError):
                        current_metric["threshold"] = 0.0
                elif low.startswith("direction:"):
                    current_metric["direction"] = line.split(":", 1)[1].strip().lower()
                elif low.startswith("statistical test:"):
                    current_metric["test"] = line.split(":", 1)[1].strip()
            elif in_outcome:
                if low.startswith("category:"):
                    current_outcome["category"] = line.split(":", 1)[1].strip().lower()
                elif low.startswith("likelihood:"):
                    try:
                        current_outcome["likelihood"] = float(
                            line.split(":")[1].strip()
                        )
                    except (ValueError, TypeError):
                        current_outcome["likelihood"] = 0.5
                elif low.startswith("impact:"):
                    current_outcome["impact"] = line.split(":", 1)[1].strip().lower()
                elif low.startswith("evidence:"):
                    current_outcome["evidence"] = [
                        e.strip() for e in line.split(":", 1)[1].split(",") if e.strip()
                    ]

        if current_metric.get("name"):
            metrics.append(self._build_metric(current_metric))
        if current_outcome.get("outcome"):
            outcomes.append(self._build_outcome(current_outcome))

        return metrics, outcomes

    def _build_metric(self, data: dict) -> EvaluationMetric:
        return EvaluationMetric(
            name=data.get("name", ""),
            description=data.get("description", ""),
            expected_value=data.get("expected", 0.5),
            threshold=data.get("threshold", 0.0),
            direction=data.get("direction", "higher_is_better"),
            statistical_test=data.get("test", ""),
        )

    def _build_outcome(self, data: dict) -> ExpectedOutcome:
        return ExpectedOutcome(
            outcome=data.get("outcome", ""),
            category=data.get("category", "secondary"),
            likelihood=data.get("likelihood", 0.5),
            impact=data.get("impact", "medium"),
            evidence=data.get("evidence", []),
        )

    def _dedup(self, defaults: list, llm_items: list) -> list:
        seen: set[str] = set()
        merged: list = []
        for item in defaults + llm_items:
            key = ""
            if isinstance(item, EvaluationMetric):
                key = item.name.lower()
            elif isinstance(item, ExpectedOutcome):
                key = item.outcome[:60].lower()
            if key and key not in seen:
                seen.add(key)
                merged.append(item)
        return merged
