from __future__ import annotations

import time

from app.core.logging import get_logger
from app.experiments.config import get_experiment_settings
from app.experiments.models import ExperimentPlan, ExperimentValidationReport

logger = get_logger("experiments.validator")
settings = get_experiment_settings()


class ExperimentValidator:
    def validate(self, plan: ExperimentPlan) -> ExperimentValidationReport:
        start = time.monotonic()
        errors: list[str] = []
        warnings: list[str] = []
        missing_baselines: list[str] = []
        missing_metrics: list[str] = []
        unsupported_hypotheses: list[str] = []
        inconsistent_variables: list[str] = []
        incomplete_protocols: list[str] = []
        reproducibility_issues: list[str] = []

        self._check_missing_baselines(plan, errors, missing_baselines)
        self._check_missing_metrics(plan, errors, missing_metrics)
        self._check_unsupported_hypotheses(plan, warnings, unsupported_hypotheses)
        self._check_inconsistent_variables(plan, warnings, inconsistent_variables)
        self._check_incomplete_protocols(plan, warnings, incomplete_protocols)
        self._check_reproducibility(plan, warnings, reproducibility_issues)

        is_valid = (
            len(errors) == 0
            and len(warnings) <= settings.max_warnings
            and len(incomplete_protocols) == 0
        )

        report = ExperimentValidationReport(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            missing_baselines=missing_baselines,
            missing_metrics=missing_metrics,
            unsupported_hypotheses=unsupported_hypotheses,
            inconsistent_variables=inconsistent_variables,
            incomplete_protocols=incomplete_protocols,
            reproducibility_issues=reproducibility_issues,
        )

        logger.info(
            "experiment validation complete",
            extra={
                "is_valid": is_valid,
                "errors": len(errors),
                "warnings": len(warnings),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )

        return report

    def validate_async(self, plan: ExperimentPlan) -> ExperimentValidationReport:
        return self.validate(plan)

    def _check_missing_baselines(
        self,
        plan: ExperimentPlan,
        errors: list[str],
        missing: list[str],
    ) -> None:
        if not plan.baselines:
            errors.append("No baseline models defined for comparison")
            missing.append("baselines")
        elif len(plan.baselines) < 2:
            warnings.append(f"Only {len(plan.baselines)} baseline(s); expected at least 2")
            missing.append("baselines")

    def _check_missing_metrics(
        self,
        plan: ExperimentPlan,
        errors: list[str],
        missing: list[str],
    ) -> None:
        if not plan.evaluation_metrics:
            errors.append("No evaluation metrics defined")
            missing.append("evaluation_metrics")
        elif len(plan.evaluation_metrics) < 2:
            warnings.append(f"Only {len(plan.evaluation_metrics)} metric(s); expected at least 2")
            missing.append("evaluation_metrics")

    def _check_unsupported_hypotheses(
        self,
        plan: ExperimentPlan,
        warnings: list[str],
        unsupported: list[str],
    ) -> None:
        for h in plan.hypotheses:
            if h.confidence < settings.hypothesis_confidence_threshold:
                warnings.append(
                    f"Hypothesis has low confidence ({h.confidence:.2f}): {h.hypothesis[:60]}"
                )
                unsupported.append(h.hypothesis[:80])
            if not h.validation_criteria:
                warnings.append(
                    f"Hypothesis missing validation criteria: {h.hypothesis[:60]}"
                )
                unsupported.append(h.hypothesis[:80])

    def _check_inconsistent_variables(
        self,
        plan: ExperimentPlan,
        warnings: list[str],
        inconsistent: list[str],
    ) -> None:
        indep_vars = [v for v in plan.variables if v.variable_type == "independent"]
        dep_vars = [v for v in plan.variables if v.variable_type == "dependent"]

        if not indep_vars:
            warnings.append("No independent variables defined")
            inconsistent.append("independent_variables")
        if not dep_vars:
            warnings.append("No dependent variables defined")
            inconsistent.append("dependent_variables")

        names = [v.name.lower() for v in plan.variables]
        if len(names) != len(set(names)):
            warnings.append("Duplicate variable names detected")
            inconsistent.append("duplicate_variable_names")

    def _check_incomplete_protocols(
        self,
        plan: ExperimentPlan,
        warnings: list[str],
        incomplete: list[str],
    ) -> None:
        if not plan.phases:
            warnings.append("No experiment phases defined")
            incomplete.append("phases")
        elif not plan.phases[-1].steps:
            warnings.append("Final experiment phase has no steps")
            incomplete.append("final_phase_steps")

        if not plan.datasets:
            warnings.append("No datasets specified for experiment")
            incomplete.append("datasets")

    def _check_reproducibility(
        self,
        plan: ExperimentPlan,
        warnings: list[str],
        issues: list[str],
    ) -> None:
        has_seed = any(
            v.name.lower() in ("random_seed", "seed")
            for v in plan.variables
        )
        if not has_seed:
            warnings.append("No random seed variable defined for reproducibility")
            issues.append("random_seed")

        if plan.resources.software_dependencies:
            total_deps = len(plan.resources.software_dependencies)
            if total_deps < 2:
                warnings.append(f"Only {total_deps} software dependencies listed")
                issues.append("software_dependencies")
