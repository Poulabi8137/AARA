from __future__ import annotations

from app.core.logging import get_logger
from app.planner.models import (
    DependencyGraph,
    ExecutionPlan,
    ResearchTask,
    ValidationReport,
)

logger = get_logger("planner.validator")


class PlanValidator:
    def validate(self, plan: ExecutionPlan) -> ValidationReport:
        report = ValidationReport()
        task_ids = {t.task_id for t in plan.tasks}

        self._check_missing_dependencies(plan.tasks, task_ids, report)
        self._check_duplicate_tasks(plan.tasks, report)
        self._check_incomplete_objectives(plan.tasks, report)

        if plan.dependency_graph:
            graph = plan.dependency_graph
            if graph.circular_dependencies:
                report.circular_dependencies = graph.circular_dependencies
                report.errors.append(
                    f"Circular dependencies detected: {len(graph.circular_dependencies)} cycle(s)"
                )

            self._check_unreachable_tasks(task_ids, graph, report)

        if not plan.steps:
            report.errors.append("Plan has no execution steps")

        if not plan.tasks:
            report.errors.append("Plan has no tasks")

        report.is_valid = len(report.errors) == 0

        if report.warnings:
            logger.info(
                "plan validation warnings",
                extra={"warning_count": len(report.warnings)},
            )

        logger.info(
            "plan validation complete",
            extra={
                "valid": report.is_valid,
                "errors": len(report.errors),
                "warnings": len(report.warnings),
            },
        )

        return report

    def _check_missing_dependencies(
        self,
        tasks: list[ResearchTask],
        task_ids: set[str],
        report: ValidationReport,
    ) -> None:
        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id not in task_ids:
                    report.missing_dependencies.append(
                        f"Task '{task.task_id}' depends on missing task '{dep_id}'"
                    )
        if report.missing_dependencies:
            report.errors.append(
                f"Missing dependencies: {len(report.missing_dependencies)}"
            )

    def _check_duplicate_tasks(
        self,
        tasks: list[ResearchTask],
        report: ValidationReport,
    ) -> None:
        seen: set[str] = set()
        for task in tasks:
            if task.task_id in seen:
                report.duplicate_tasks.append(task.task_id)
            seen.add(task.task_id)
        if report.duplicate_tasks:
            report.errors.append(
                f"Duplicate tasks: {len(report.duplicate_tasks)}"
            )

    def _check_incomplete_objectives(
        self,
        tasks: list[ResearchTask],
        report: ValidationReport,
    ) -> None:
        for task in tasks:
            if not task.objective or len(task.objective.strip()) < 10:
                report.incomplete_objectives.append(task.task_id)
                report.warnings.append(
                    f"Task '{task.task_id}' has incomplete objective"
                )

    def _check_unreachable_tasks(
        self,
        task_ids: set[str],
        graph: DependencyGraph,
        report: ValidationReport,
    ) -> None:
        if not graph.execution_order:
            return
        ordered_ids = set()
        for level in graph.execution_order:
            for tid in level:
                ordered_ids.add(tid)
        unreachable = task_ids - ordered_ids
        if unreachable:
            report.unreachable_tasks = list(unreachable)
            report.errors.append(
                f"Unreachable tasks: {len(unreachable)}"
            )
