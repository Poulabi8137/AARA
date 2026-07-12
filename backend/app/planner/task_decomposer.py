from __future__ import annotations

import uuid

from app.core.logging import get_logger
from app.planner.config import get_planner_settings
from app.planner.models import (
    ResearchGoal,
    ResearchTask,
    TaskComplexity,
    TaskType,
)
from app.rag.models import SearchIntent

logger = get_logger("planner.task_decomposer")
settings = get_planner_settings()

_INTENT_TASK_MAP: dict[SearchIntent, list[TaskType]] = {
    SearchIntent.FACTUAL: [TaskType.LITERATURE_REVIEW],
    SearchIntent.EXPLORATORY: [
        TaskType.SURVEY,
        TaskType.LITERATURE_REVIEW,
        TaskType.RESEARCH_SYNTHESIS,
    ],
    SearchIntent.COMPARATIVE: [
        TaskType.LITERATURE_REVIEW,
        TaskType.COMPARISON,
        TaskType.RESEARCH_SYNTHESIS,
    ],
    SearchIntent.METHODOLOGICAL: [
        TaskType.LITERATURE_REVIEW,
        TaskType.METHODOLOGY_DESIGN,
        TaskType.BENCHMARK_ANALYSIS,
    ],
    SearchIntent.CRITICAL: [
        TaskType.LITERATURE_REVIEW,
        TaskType.PAPER_ANALYSIS,
        TaskType.RESEARCH_SYNTHESIS,
    ],
    SearchIntent.SUMMARIZATION: [TaskType.RESEARCH_SYNTHESIS],
}

_COMPLEXITY_BONUS: dict[TaskComplexity, list[TaskType]] = {
    TaskComplexity.MODERATE: [
        TaskType.DATASET_DISCOVERY,
        TaskType.PAPER_ANALYSIS,
    ],
    TaskComplexity.COMPLEX: [
        TaskType.DATASET_DISCOVERY,
        TaskType.PAPER_ANALYSIS,
        TaskType.EXPERIMENT_PLANNING,
        TaskType.BENCHMARK_ANALYSIS,
    ],
}

_TASK_PRIORITIES: dict[TaskType, int] = {
    TaskType.LITERATURE_REVIEW: 8,
    TaskType.SURVEY: 7,
    TaskType.COMPARISON: 6,
    TaskType.EXPERIMENT_PLANNING: 9,
    TaskType.BENCHMARK_ANALYSIS: 7,
    TaskType.DATASET_DISCOVERY: 5,
    TaskType.PAPER_ANALYSIS: 6,
    TaskType.RESEARCH_SYNTHESIS: 4,
    TaskType.METHODOLOGY_DESIGN: 8,
}

_TASK_DESCRIPTIONS: dict[TaskType, tuple[str, str, str]] = {
    TaskType.LITERATURE_REVIEW: (
        "Review existing literature",
        "Search and retrieve relevant papers, articles, and publications on the topic",
        "Annotated bibliography with key findings",
    ),
    TaskType.SURVEY: (
        "Conduct broad survey",
        "Survey the research landscape to identify major themes, trends, and approaches",
        "Survey report with categorized findings",
    ),
    TaskType.COMPARISON: (
        "Perform comparative analysis",
        "Compare and contrast different approaches, methods, or findings",
        "Comparison matrix with analysis",
    ),
    TaskType.EXPERIMENT_PLANNING: (
        "Design experiment plan",
        "Plan experimental methodology including variables, procedures, and evaluation criteria",
        "Experiment design document",
    ),
    TaskType.BENCHMARK_ANALYSIS: (
        "Analyze benchmarks",
        "Evaluate performance metrics and benchmark results from existing research",
        "Benchmark analysis report",
    ),
    TaskType.DATASET_DISCOVERY: (
        "Discover relevant datasets",
        "Identify and evaluate datasets suitable for the research task",
        "Dataset catalog with evaluation",
    ),
    TaskType.PAPER_ANALYSIS: (
        "Analyze individual papers",
        "Perform deep analysis on key papers including methodology, results, and limitations",
        "Paper analysis reports",
    ),
    TaskType.RESEARCH_SYNTHESIS: (
        "Synthesize findings",
        "Synthesize all collected evidence into a coherent research summary",
        "Synthesized research output",
    ),
    TaskType.METHODOLOGY_DESIGN: (
        "Design research methodology",
        "Develop a structured methodology for the research investigation",
        "Methodology specification document",
    ),
}


class TaskDecomposer:
    def decompose(
        self,
        goal: ResearchGoal,
        keywords: list[str],
    ) -> list[ResearchTask]:
        task_types = self._select_task_types(goal)
        tasks: list[ResearchTask] = []
        order = 0

        for tt in task_types:
            if len(tasks) >= settings.max_task_count:
                break
            order += 1
            obj, desc, output = _TASK_DESCRIPTIONS[tt]
            task = ResearchTask(
                task_id=self._make_id(goal, tt, order),
                type=tt,
                objective=f"{obj}: {goal.objective[:80]}",
                description=f"{desc}. Keywords: {', '.join(keywords[:6])}",
                expected_output=output,
                priority=_TASK_PRIORITIES[tt],
                required_evidence=keywords[:5],
            )
            tasks.append(task)

        self._assign_dependencies(tasks)

        logger.info(
            "task decomposition complete",
            extra={
                "goal": goal.objective[:60],
                "task_count": len(tasks),
                "task_types": [t.type.value for t in tasks],
            },
        )
        return tasks

    def _select_task_types(self, goal: ResearchGoal) -> list[TaskType]:
        base = list(_INTENT_TASK_MAP.get(goal.intent, [TaskType.LITERATURE_REVIEW]))
        bonus = _COMPLEXITY_BONUS.get(goal.complexity, [])
        seen: set[TaskType] = set()
        result: list[TaskType] = []
        for tt in base + bonus:
            if tt not in seen:
                seen.add(tt)
                result.append(tt)
        return result

    def _make_id(self, goal: ResearchGoal, tt: TaskType, order: int) -> str:
        prefix = goal.intent.value[:4]
        return f"{prefix}_{tt.value}_{order}_{uuid.uuid4().hex[:6]}"

    def _assign_dependencies(self, tasks: list[ResearchTask]) -> None:
        for i, task in enumerate(tasks):
            if i == 0:
                continue
            task.dependencies.append(tasks[i - 1].task_id)
            if i >= 2:
                task.dependencies.append(tasks[i - 2].task_id)
