from __future__ import annotations

from app.core.logging import get_logger
from app.planner.config import get_planner_settings
from app.planner.models import (
    ResearchTask,
    RetrievalPlan,
    TaskType,
)
from app.rag.models import ALL_COLLECTIONS, RetrievalStrategy, SourceType

logger = get_logger("planner.retrieval_planner")
settings = get_planner_settings()

_TASK_COLLECTION_MAP: dict[TaskType, list[SourceType]] = {
    TaskType.LITERATURE_REVIEW: [
        SourceType.CHROMA_PAPER,
        SourceType.CHROMA_CITATION,
        SourceType.MEMORY_PAPER,
        SourceType.MEMORY_LONG_TERM,
        SourceType.CHROMA_KNOWLEDGE,
    ],
    TaskType.SURVEY: [
        SourceType.CHROMA_PAPER,
        SourceType.CHROMA_WEB,
        SourceType.CHROMA_REPORT,
        SourceType.CHROMA_KNOWLEDGE,
        SourceType.MEMORY_LONG_TERM,
    ],
    TaskType.COMPARISON: [
        SourceType.CHROMA_PAPER,
        SourceType.CHROMA_CITATION,
        SourceType.MEMORY_PAPER,
        SourceType.MEMORY_LONG_TERM,
    ],
    TaskType.EXPERIMENT_PLANNING: [
        SourceType.MEMORY_PROJECT,
        SourceType.MEMORY_SESSION,
        SourceType.CHROMA_PAPER,
        SourceType.CHROMA_KNOWLEDGE,
    ],
    TaskType.BENCHMARK_ANALYSIS: [
        SourceType.CHROMA_PAPER,
        SourceType.CHROMA_KNOWLEDGE,
        SourceType.CHROMA_REPORT,
        SourceType.MEMORY_LONG_TERM,
    ],
    TaskType.DATASET_DISCOVERY: [
        SourceType.CHROMA_PAPER,
        SourceType.CHROMA_WEB,
        SourceType.CHROMA_KNOWLEDGE,
        SourceType.MEMORY_LONG_TERM,
    ],
    TaskType.PAPER_ANALYSIS: [
        SourceType.CHROMA_PAPER,
        SourceType.CHROMA_CITATION,
        SourceType.MEMORY_PAPER,
    ],
    TaskType.RESEARCH_SYNTHESIS: [
        SourceType.CHROMA_REPORT,
        SourceType.CHROMA_PAPER,
        SourceType.MEMORY_LONG_TERM,
        SourceType.MEMORY_PROJECT,
    ],
    TaskType.METHODOLOGY_DESIGN: [
        SourceType.CHROMA_PAPER,
        SourceType.CHROMA_KNOWLEDGE,
        SourceType.MEMORY_PAPER,
        SourceType.MEMORY_PROJECT,
    ],
}


class RetrievalPlanner:
    def plan_for_task(self, task: ResearchTask) -> RetrievalPlan:
        base_collections = _TASK_COLLECTION_MAP.get(task.type, list(ALL_COLLECTIONS))
        plan = RetrievalPlan(
            collections=base_collections,
            strategy=self._select_strategy(task),
            depth=self._select_depth(task),
            confidence_threshold=settings.confidence_threshold,
            citation_required=self._needs_citations(task),
            memory_usage=True,
            external_search=(
                task.type
                in {
                    TaskType.SURVEY,
                    TaskType.DATASET_DISCOVERY,
                    TaskType.LITERATURE_REVIEW,
                }
            ),
        )
        return plan

    def plan_for_tasks(
        self,
        tasks: list[ResearchTask],
    ) -> dict[str, RetrievalPlan]:
        return {t.task_id: self.plan_for_task(t) for t in tasks}

    def _select_strategy(self, task: ResearchTask) -> RetrievalStrategy:
        if task.type in {
            TaskType.COMPARISON,
            TaskType.METHODOLOGY_DESIGN,
            TaskType.LITERATURE_REVIEW,
        }:
            return RetrievalStrategy.HYBRID
        return RetrievalStrategy.SEMANTIC

    def _select_depth(self, task: ResearchTask) -> int:
        if task.type in {
            TaskType.SURVEY,
            TaskType.LITERATURE_REVIEW,
            TaskType.COMPARISON,
        }:
            return max(settings.max_planning_depth, 10)
        return settings.max_planning_depth

    def _needs_citations(self, task: ResearchTask) -> bool:
        return task.type in {
            TaskType.LITERATURE_REVIEW,
            TaskType.PAPER_ANALYSIS,
            TaskType.COMPARISON,
        }
