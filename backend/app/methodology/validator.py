from __future__ import annotations

import time

from app.core.logging import get_logger
from app.methodology.config import get_methodology_settings
from app.methodology.models import MethodologyResult, MethodologyValidationReport

logger = get_logger("methodology.validator")
settings = get_methodology_settings()


class MethodologyValidator:
    def validate(self, result: MethodologyResult) -> MethodologyValidationReport:
        start = time.monotonic()
        errors: list[str] = []
        warnings: list[str] = []
        missing_datasets: list[str] = []
        missing_benchmarks: list[str] = []
        weak_evaluation: list[str] = []
        incomplete_validation: list[str] = []

        self._check_missing_datasets(result, warnings, missing_datasets)
        self._check_missing_benchmarks(result, warnings, missing_benchmarks)
        self._check_weak_evaluation(result, warnings, weak_evaluation)
        self._check_incomplete_validation(result, errors, incomplete_validation)

        is_valid = len(errors) == 0 and len(warnings) <= settings.max_warnings

        report = MethodologyValidationReport(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            missing_datasets=missing_datasets,
            missing_benchmarks=missing_benchmarks,
            weak_evaluation=weak_evaluation,
            incomplete_validation=incomplete_validation,
        )

        logger.info(
            "methodology validation complete",
            extra={
                "is_valid": is_valid,
                "errors": len(errors),
                "warnings": len(warnings),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )

        return report

    def validate_async(self, result: MethodologyResult) -> MethodologyValidationReport:
        return self.validate(result)

    def _check_missing_datasets(
        self,
        result: MethodologyResult,
        warnings: list[str],
        missing: list[str],
    ) -> None:
        if result.methods and not result.datasets:
            warnings.append("Methods recommended but no datasets provided")
            missing.append("recommended_datasets")

    def _check_missing_benchmarks(
        self,
        result: MethodologyResult,
        warnings: list[str],
        missing: list[str],
    ) -> None:
        if result.methods and not result.benchmarks:
            warnings.append("Methods recommended but no benchmarks provided")
            missing.append("recommended_benchmarks")

    def _check_weak_evaluation(
        self,
        result: MethodologyResult,
        warnings: list[str],
        weak: list[str],
    ) -> None:
        if result.protocol:
            if len(result.protocol.metrics) < 2:
                warnings.append(
                    f"Only {len(result.protocol.metrics)} metric(s) specified; expected at least 2"
                )
                weak.append("evaluation_protocol.metrics")
            if not result.protocol.baselines:
                warnings.append("No baseline methods specified for comparison")
                weak.append("evaluation_protocol.baselines")

    def _check_incomplete_validation(
        self,
        result: MethodologyResult,
        errors: list[str],
        incomplete: list[str],
    ) -> None:
        if not result.validation_strategies:
            errors.append("No validation strategies defined")
            incomplete.append("validation_strategies")
