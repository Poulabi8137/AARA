from __future__ import annotations

import time
from typing import Any

from app.analysis.models import AnalysisResult
from app.core.logging import get_logger
from app.experiments.baselines import BaselineBenchmarkPlanner
from app.experiments.config import get_experiment_settings
from app.experiments.design import ExperimentDesigner
from app.experiments.evaluation import EvaluationPlanner
from app.experiments.hypothesis import HypothesisGenerator
from app.experiments.models import (
    ExperimentMetadata,
    ExperimentPlan,
    ExperimentStatistics,
    ExperimentTimeline,
)
from app.experiments.resources import ResourcePlanner
from app.experiments.risks import ExperimentRiskAnalyzer
from app.experiments.validator import ExperimentValidator
from app.experiments.variables import VariablePlanner
from app.methodology.models import MethodologyResult
from app.rag.llm import RAGLLMProvider

logger = get_logger("experiments.orchestrator")
settings = get_experiment_settings()


class ExperimentPlanner:
    def __init__(
        self,
        llm: RAGLLMProvider | None = None,
        hypothesis_generator: HypothesisGenerator | None = None,
        experiment_designer: ExperimentDesigner | None = None,
        variable_planner: VariablePlanner | None = None,
        baseline_planner: BaselineBenchmarkPlanner | None = None,
        resource_planner: ResourcePlanner | None = None,
        evaluation_planner: EvaluationPlanner | None = None,
        risk_analyzer: ExperimentRiskAnalyzer | None = None,
        validator: ExperimentValidator | None = None,
    ):
        self._llm = llm
        self._hypothesis_gen = hypothesis_generator or HypothesisGenerator(llm)
        self._designer = experiment_designer or ExperimentDesigner(llm)
        self._variable_planner = variable_planner or VariablePlanner(llm)
        self._baseline_planner = baseline_planner or BaselineBenchmarkPlanner(llm)
        self._resource_planner = resource_planner or ResourcePlanner(llm)
        self._evaluation_planner = evaluation_planner or EvaluationPlanner(llm)
        self._risk_analyzer = risk_analyzer or ExperimentRiskAnalyzer(llm)
        self._validator = validator or ExperimentValidator()

    async def plan(
        self,
        query: str,
        analysis_result: AnalysisResult,
        methodology_result: MethodologyResult,
        domain: str | None = None,
        complexity: str | None = None,
        user_id: Any = None,
        project_id: Any = None,
    ) -> ExperimentPlan:
        start = time.monotonic()

        hypotheses = await self._hypothesis_gen.generate(
            query,
            analysis_result,
            methodology_result,
        )

        objectives, phases, datasets = await self._designer.design(
            query,
            analysis_result,
            methodology_result,
            hypotheses,
        )

        variables = await self._variable_planner.plan(
            query,
            analysis_result,
            methodology_result,
            hypotheses,
        )

        baselines, benchmarks = await self._baseline_planner.plan(
            query,
            methodology_result,
        )

        resources = await self._resource_planner.estimate(
            query,
            methodology_result,
            phases,
        )

        metrics, outcomes = await self._evaluation_planner.plan(
            query,
            methodology_result,
            phases,
        )

        risks = await self._risk_analyzer.analyze(
            query,
            methodology_result,
            phases,
        )

        timeline = self._build_timeline(phases, risks)

        stats = self._build_statistics(
            hypotheses,
            phases,
            variables,
            baselines,
            risks,
            metrics,
            timeline,
        )

        plan = ExperimentPlan(
            query=query[:500],
            objectives=objectives,
            hypotheses=hypotheses,
            phases=phases,
            variables=variables,
            datasets=datasets,
            benchmarks=benchmarks,
            baselines=baselines,
            evaluation_metrics=metrics,
            expected_outcomes=outcomes,
            risks=risks,
            timeline=timeline,
            resources=resources,
            statistics=stats,
        )

        validation = self._validator.validate(plan)
        duration = time.monotonic() - start

        metadata = ExperimentMetadata(
            duration_ms=round(duration * 1000, 1),
            model=settings.model,
            complexity=complexity or settings.experiment_complexity,
            validation_passed=validation.is_valid,
            validation_errors=validation.errors,
        )
        plan.metadata = metadata
        plan.validation = validation

        logger.info(
            "experiment planning complete",
            extra={
                "hypotheses": len(hypotheses),
                "objectives": len(objectives),
                "phases": len(phases),
                "variables": len(variables),
                "baselines": len(baselines),
                "benchmarks": len(benchmarks),
                "metrics": len(metrics),
                "risks": len(risks),
                "valid": validation.is_valid,
                "duration_ms": metadata.duration_ms,
            },
        )

        return plan

    def _build_timeline(
        self,
        phases: list,
        risks: list,
    ) -> ExperimentTimeline:
        total_minutes = sum(getattr(p, "estimated_duration_minutes", 0) for p in phases)
        total_days = max(1, total_minutes // (8 * 60))

        milestones = [
            "Phase 1: Data preparation complete",
            "Phase 2: Implementation complete",
            "Phase 3: Training complete",
            f"Phase {len(phases)}: Final evaluation complete",
        ]

        return ExperimentTimeline(
            total_estimated_days=total_days,
            phases=[getattr(p, "name", f"phase_{i}") for i, p in enumerate(phases)],
            milestones=milestones[: len(phases)],
            critical_path=[
                getattr(p, "name", "")
                for p in phases
                if getattr(p, "estimated_duration_minutes", 0) > 300
            ],
        )

    def _build_statistics(
        self,
        hypotheses: list,
        phases: list,
        variables: list,
        baselines: list,
        risks: list,
        metrics: list,
        timeline: ExperimentTimeline,
    ) -> ExperimentStatistics:
        total_steps = sum(len(getattr(p, "steps", [])) for p in phases)
        confidence = self._compute_confidence(hypotheses)

        return ExperimentStatistics(
            total_hypotheses=len(hypotheses),
            total_phases=len(phases),
            total_steps=total_steps,
            total_variables=len(variables),
            total_baselines=len(baselines),
            total_risks=len(risks),
            total_metrics=len(metrics),
            estimated_days=timeline.total_estimated_days,
            overall_confidence=confidence,
        )

    def _compute_confidence(self, hypotheses: list) -> float:
        if not hypotheses:
            return 0.0
        return sum(getattr(h, "confidence", 0.5) for h in hypotheses) / len(hypotheses)
