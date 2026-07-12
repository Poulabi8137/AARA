from __future__ import annotations

import time

from app.analysis.models import AnalysisResult
from app.core.logging import get_logger
from app.methodology.benchmark_recommender import BenchmarkRecommender
from app.methodology.best_practices import BestPracticesEngine
from app.methodology.config import get_methodology_settings
from app.methodology.dataset_recommender import DatasetRecommender
from app.methodology.evaluation_protocol import EvaluationProtocolDesigner
from app.methodology.method_selector import MethodSelector
from app.methodology.models import (
    MethodologyMetadata,
    MethodologyProfile,
    MethodologyRequest,
    MethodologyResult,
    MethodologyStatistics,
)
from app.methodology.risk_assessment import RiskAssessor
from app.methodology.validation_strategy import ValidationStrategyDesigner
from app.methodology.validator import MethodologyValidator
from app.rag.llm import RAGLLMProvider

logger = get_logger("methodology.orchestrator")
settings = get_methodology_settings()


class MethodologyEngine:
    def __init__(
        self,
        llm: RAGLLMProvider | None = None,
        method_selector: MethodSelector | None = None,
        dataset_recommender: DatasetRecommender | None = None,
        benchmark_recommender: BenchmarkRecommender | None = None,
        evaluation_designer: EvaluationProtocolDesigner | None = None,
        validation_designer: ValidationStrategyDesigner | None = None,
        risk_assessor: RiskAssessor | None = None,
        best_practices: BestPracticesEngine | None = None,
        validator: MethodologyValidator | None = None,
    ):
        self._llm = llm
        self._method_selector = method_selector or MethodSelector(llm)
        self._dataset_recommender = dataset_recommender or DatasetRecommender(llm)
        self._benchmark_recommender = benchmark_recommender or BenchmarkRecommender(llm)
        self._evaluation_designer = evaluation_designer or EvaluationProtocolDesigner(
            llm
        )
        self._validation_designer = validation_designer or ValidationStrategyDesigner(
            llm
        )
        self._risk_assessor = risk_assessor or RiskAssessor(llm)
        self._best_practices = best_practices or BestPracticesEngine(llm)
        self._validator = validator or MethodologyValidator()

    async def run(self, request: MethodologyRequest) -> MethodologyResult:
        start = time.monotonic()

        profile = self._build_profile(request)

        methods = await self._method_selector.select(
            request.query, request.analysis_result
        )
        method_names = [m.method for m in methods]

        analysis_result: AnalysisResult = request.analysis_result

        datasets = await self._dataset_recommender.recommend(
            request.query,
            analysis_result,
            method_names,
        )

        benchmarks = await self._benchmark_recommender.recommend(
            request.query,
            method_names,
        )

        evaluation = await self._evaluation_designer.design(
            request.query,
            analysis_result,
            method_names,
        )

        validation_strategies = await self._validation_designer.design(
            request.query,
            analysis_result,
        )

        risks = await self._risk_assessor.assess(
            request.query,
            analysis_result,
        )

        practices = await self._best_practices.generate(
            request.query,
            analysis_result,
        )

        stats = self._build_statistics(
            methods,
            datasets,
            benchmarks,
            risks,
            practices,
        )

        result = MethodologyResult(
            profile=profile,
            methods=methods,
            datasets=datasets,
            benchmarks=benchmarks,
            protocol=evaluation,
            validation_strategies=validation_strategies,
            risks=risks,
            best_practices=practices,
            statistics=stats,
        )

        validation = self._validator.validate(result)
        duration = time.monotonic() - start

        metadata = MethodologyMetadata(
            duration_ms=round(duration * 1000, 1),
            model=settings.model,
            validation_passed=validation.is_valid,
            validation_errors=validation.errors,
        )
        result.metadata = metadata
        result.validation = validation

        logger.info(
            "methodology analysis complete",
            extra={
                "methods": len(methods),
                "datasets": len(datasets),
                "benchmarks": len(benchmarks),
                "risks": len(risks),
                "practices": len(practices),
                "valid": validation.is_valid,
                "duration_ms": metadata.duration_ms,
            },
        )

        return result

    def _build_profile(self, request: MethodologyRequest) -> MethodologyProfile:
        return MethodologyProfile(
            domain=request.domain or "",
            complexity=getattr(request.analysis_result, "complexity", "moderate"),
            evidence_quality=getattr(
                request.analysis_result.confidence, "overall", 0.0
            ),
            research_goal=request.query[:200],
        )

    def _build_statistics(
        self,
        methods: list,
        datasets: list,
        benchmarks: list,
        risks: list,
        practices: list,
    ) -> MethodologyStatistics:
        return MethodologyStatistics(
            total_methods=len(methods),
            total_datasets=len(datasets),
            total_benchmarks=len(benchmarks),
            total_risks=len(risks),
            total_practices=len(practices),
            overall_confidence=self._compute_confidence(methods),
        )

    def _compute_confidence(self, methods: list) -> float:
        if not methods:
            return 0.0
        return sum(getattr(m, "confidence", 0.5) for m in methods) / len(methods)
