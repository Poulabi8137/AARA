from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.logging import get_logger
from app.planner.models import (
    AgentType,
    DependencyType,
    ExecutionStep,
    ResearchGoal,
    ResearchStrategyType,
    ResearchTask,
    RetrievalPlan,
    TaskDependency,
    TaskType,
    TaskComplexity,
)
from app.rag.models import ALL_COLLECTIONS, RetrievalStrategy, SearchIntent, SourceType

logger = get_logger("planner.strategies")


class ResearchStrategy(ABC):
    @property
    @abstractmethod
    def strategy_type(self) -> ResearchStrategyType:
        ...

    @abstractmethod
    def decompose(self, goal: ResearchGoal, keywords: list[str]) -> list[ResearchTask]:
        ...

    @abstractmethod
    def create_dependencies(self, tasks: list[ResearchTask]) -> list[TaskDependency]:
        ...

    @abstractmethod
    def create_retrieval_plan(self, tasks: list[ResearchTask]) -> RetrievalPlan:
        ...

    @abstractmethod
    def assign_agents(self, tasks: list[ResearchTask]) -> dict[str, AgentType]:
        ...


class LiteratureReviewStrategy(ResearchStrategy):
    strategy_type = ResearchStrategyType.LITERATURE_REVIEW

    def decompose(self, goal: ResearchGoal, keywords: list[str]) -> list[ResearchTask]:
        return [
            ResearchTask(
                task_id=f"lr_1_{goal.intent.value}",
                type=TaskType.LITERATURE_REVIEW,
                objective=f"Comprehensive literature review: {goal.objective[:80]}",
                description=f"Search and retrieve all relevant papers on {', '.join(keywords[:6])}",
                expected_output="Annotated bibliography with key findings and citations",
                priority=8,
            ),
            ResearchTask(
                task_id=f"lr_2_{goal.intent.value}",
                type=TaskType.PAPER_ANALYSIS,
                objective=f"Analyze key papers: {goal.objective[:80]}",
                description="Deep analysis of methodology, results, and limitations of key papers",
                expected_output="Paper analysis reports with critical evaluation",
                priority=6,
            ),
            ResearchTask(
                task_id=f"lr_3_{goal.intent.value}",
                type=TaskType.RESEARCH_SYNTHESIS,
                objective=f"Synthesize literature findings: {goal.objective[:80]}",
                description="Synthesize all findings into coherent research summary",
                expected_output="Synthesized literature review output",
                priority=4,
            ),
        ]

    def create_dependencies(self, tasks: list[ResearchTask]) -> list[TaskDependency]:
        return [
            TaskDependency(task_id=tasks[1].task_id, depends_on=tasks[0].task_id, dependency_type=DependencyType.BLOCKING),
            TaskDependency(task_id=tasks[2].task_id, depends_on=tasks[1].task_id, dependency_type=DependencyType.BLOCKING),
        ]

    def create_retrieval_plan(self, tasks: list[ResearchTask]) -> RetrievalPlan:
        return RetrievalPlan(
            collections=[
                SourceType.CHROMA_PAPER,
                SourceType.CHROMA_CITATION,
                SourceType.CHROMA_KNOWLEDGE,
                SourceType.MEMORY_PAPER,
                SourceType.MEMORY_LONG_TERM,
            ],
            strategy=RetrievalStrategy.HYBRID,
            depth=10,
            citation_required=True,
            memory_usage=True,
            external_search=True,
        )

    def assign_agents(self, tasks: list[ResearchTask]) -> dict[str, AgentType]:
        return {
            tasks[0].task_id: AgentType.RETRIEVER,
            tasks[1].task_id: AgentType.ANALYZER,
            tasks[2].task_id: AgentType.SUMMARIZER,
        }


class ComparativeAnalysisStrategy(ResearchStrategy):
    strategy_type = ResearchStrategyType.COMPARATIVE_ANALYSIS

    def decompose(self, goal: ResearchGoal, keywords: list[str]) -> list[ResearchTask]:
        return [
            ResearchTask(
                task_id=f"ca_1_{goal.intent.value}",
                type=TaskType.LITERATURE_REVIEW,
                objective=f"Gather comparative literature: {goal.objective[:80]}",
                description=f"Collect papers and data for comparison on {', '.join(keywords[:6])}",
                expected_output="Collected literature for comparison",
                priority=8,
            ),
            ResearchTask(
                task_id=f"ca_2_{goal.intent.value}",
                type=TaskType.COMPARISON,
                objective=f"Perform comparison: {goal.objective[:80]}",
                description="Compare and contrast approaches, methods, or findings across sources",
                expected_output="Comparison matrix with analysis",
                priority=7,
            ),
            ResearchTask(
                task_id=f"ca_3_{goal.intent.value}",
                type=TaskType.RESEARCH_SYNTHESIS,
                objective=f"Synthesize comparison: {goal.objective[:80]}",
                description="Synthesize comparative findings into final output",
                expected_output="Comparative analysis report",
                priority=4,
            ),
        ]

    def create_dependencies(self, tasks: list[ResearchTask]) -> list[TaskDependency]:
        return [
            TaskDependency(task_id=tasks[1].task_id, depends_on=tasks[0].task_id, dependency_type=DependencyType.BLOCKING),
            TaskDependency(task_id=tasks[2].task_id, depends_on=tasks[1].task_id, dependency_type=DependencyType.BLOCKING),
        ]

    def create_retrieval_plan(self, tasks: list[ResearchTask]) -> RetrievalPlan:
        return RetrievalPlan(
            collections=[
                SourceType.CHROMA_PAPER,
                SourceType.CHROMA_CITATION,
                SourceType.MEMORY_PAPER,
                SourceType.MEMORY_LONG_TERM,
                SourceType.CHROMA_KNOWLEDGE,
            ],
            strategy=RetrievalStrategy.HYBRID,
            depth=10,
            citation_required=True,
            memory_usage=True,
            external_search=False,
        )

    def assign_agents(self, tasks: list[ResearchTask]) -> dict[str, AgentType]:
        return {
            tasks[0].task_id: AgentType.RETRIEVER,
            tasks[1].task_id: AgentType.ANALYZER,
            tasks[2].task_id: AgentType.SUMMARIZER,
        }


class ExperimentalStrategy(ResearchStrategy):
    strategy_type = ResearchStrategyType.EXPERIMENTAL

    def decompose(self, goal: ResearchGoal, keywords: list[str]) -> list[ResearchTask]:
        return [
            ResearchTask(
                task_id=f"ex_1_{goal.intent.value}",
                type=TaskType.LITERATURE_REVIEW,
                objective=f"Review existing experimental work: {goal.objective[:80]}",
                description=f"Review related experimental methodologies for {', '.join(keywords[:6])}",
                expected_output="Existing methodology summary",
                priority=8,
            ),
            ResearchTask(
                task_id=f"ex_2_{goal.intent.value}",
                type=TaskType.EXPERIMENT_PLANNING,
                objective=f"Design experiment: {goal.objective[:80]}",
                description="Plan experimental design including variables and evaluation criteria",
                expected_output="Experiment design document",
                priority=9,
            ),
            ResearchTask(
                task_id=f"ex_3_{goal.intent.value}",
                type=TaskType.METHODOLOGY_DESIGN,
                objective=f"Design methodology: {goal.objective[:80]}",
                description="Develop structured methodology for the experiment",
                expected_output="Methodology specification",
                priority=8,
            ),
        ]

    def create_dependencies(self, tasks: list[ResearchTask]) -> list[TaskDependency]:
        return [
            TaskDependency(task_id=tasks[1].task_id, depends_on=tasks[0].task_id, dependency_type=DependencyType.BLOCKING),
            TaskDependency(task_id=tasks[2].task_id, depends_on=tasks[0].task_id, dependency_type=DependencyType.PARALLEL),
            TaskDependency(task_id=tasks[2].task_id, depends_on=tasks[1].task_id, dependency_type=DependencyType.SEQUENTIAL),
        ]

    def create_retrieval_plan(self, tasks: list[ResearchTask]) -> RetrievalPlan:
        return RetrievalPlan(
            collections=[
                SourceType.CHROMA_PAPER,
                SourceType.CHROMA_KNOWLEDGE,
                SourceType.MEMORY_PROJECT,
                SourceType.MEMORY_SESSION,
                SourceType.MEMORY_LONG_TERM,
            ],
            strategy=RetrievalStrategy.HYBRID,
            depth=8,
            citation_required=False,
            memory_usage=True,
            external_search=False,
        )

    def assign_agents(self, tasks: list[ResearchTask]) -> dict[str, AgentType]:
        return {
            tasks[0].task_id: AgentType.RETRIEVER,
            tasks[1].task_id: AgentType.EXPERIMENT,
            tasks[2].task_id: AgentType.METHODOLOGY,
        }


class SurveyStrategy(ResearchStrategy):
    strategy_type = ResearchStrategyType.SURVEY

    def decompose(self, goal: ResearchGoal, keywords: list[str]) -> list[ResearchTask]:
        return [
            ResearchTask(
                task_id=f"sv_1_{goal.intent.value}",
                type=TaskType.SURVEY,
                objective=f"Conduct broad survey: {goal.objective[:80]}",
                description=f"Survey research landscape for {', '.join(keywords[:6])}",
                expected_output="Survey report with categorized findings",
                priority=7,
            ),
            ResearchTask(
                task_id=f"sv_2_{goal.intent.value}",
                type=TaskType.LITERATURE_REVIEW,
                objective=f"Deep literature review: {goal.objective[:80]}",
                description="Deep dive into key papers identified in survey",
                expected_output="Annotated bibliography",
                priority=6,
            ),
            ResearchTask(
                task_id=f"sv_3_{goal.intent.value}",
                type=TaskType.RESEARCH_SYNTHESIS,
                objective=f"Synthesize survey: {goal.objective[:80]}",
                description="Synthesize survey findings into comprehensive overview",
                expected_output="Survey synthesis report",
                priority=4,
            ),
        ]

    def create_dependencies(self, tasks: list[ResearchTask]) -> list[TaskDependency]:
        return [
            TaskDependency(task_id=tasks[1].task_id, depends_on=tasks[0].task_id, dependency_type=DependencyType.BLOCKING),
            TaskDependency(task_id=tasks[2].task_id, depends_on=tasks[1].task_id, dependency_type=DependencyType.BLOCKING),
        ]

    def create_retrieval_plan(self, tasks: list[ResearchTask]) -> RetrievalPlan:
        return RetrievalPlan(
            collections=[
                SourceType.CHROMA_PAPER,
                SourceType.CHROMA_WEB,
                SourceType.CHROMA_REPORT,
                SourceType.CHROMA_KNOWLEDGE,
                SourceType.MEMORY_LONG_TERM,
            ],
            strategy=RetrievalStrategy.SEMANTIC,
            depth=12,
            citation_required=False,
            memory_usage=True,
            external_search=True,
        )

    def assign_agents(self, tasks: list[ResearchTask]) -> dict[str, AgentType]:
        return {
            tasks[0].task_id: AgentType.RETRIEVER,
            tasks[1].task_id: AgentType.RETRIEVER,
            tasks[2].task_id: AgentType.SUMMARIZER,
        }


class BenchmarkStrategy(ResearchStrategy):
    strategy_type = ResearchStrategyType.BENCHMARK

    def decompose(self, goal: ResearchGoal, keywords: list[str]) -> list[ResearchTask]:
        return [
            ResearchTask(
                task_id=f"bm_1_{goal.intent.value}",
                type=TaskType.LITERATURE_REVIEW,
                objective=f"Collect benchmark literature: {goal.objective[:80]}",
                description=f"Find papers with benchmark results on {', '.join(keywords[:6])}",
                expected_output="Benchmark paper collection",
                priority=7,
            ),
            ResearchTask(
                task_id=f"bm_2_{goal.intent.value}",
                type=TaskType.BENCHMARK_ANALYSIS,
                objective=f"Analyze benchmarks: {goal.objective[:80]}",
                description="Analyze performance metrics and benchmark results",
                expected_output="Benchmark analysis report",
                priority=7,
            ),
            ResearchTask(
                task_id=f"bm_3_{goal.intent.value}",
                type=TaskType.RESEARCH_SYNTHESIS,
                objective=f"Synthesize benchmark findings: {goal.objective[:80]}",
                description="Synthesize benchmark comparisons into final report",
                expected_output="Benchmark comparison report",
                priority=4,
            ),
        ]

    def create_dependencies(self, tasks: list[ResearchTask]) -> list[TaskDependency]:
        return [
            TaskDependency(task_id=tasks[1].task_id, depends_on=tasks[0].task_id, dependency_type=DependencyType.BLOCKING),
            TaskDependency(task_id=tasks[2].task_id, depends_on=tasks[1].task_id, dependency_type=DependencyType.BLOCKING),
        ]

    def create_retrieval_plan(self, tasks: list[ResearchTask]) -> RetrievalPlan:
        return RetrievalPlan(
            collections=[
                SourceType.CHROMA_PAPER,
                SourceType.CHROMA_KNOWLEDGE,
                SourceType.CHROMA_REPORT,
                SourceType.MEMORY_LONG_TERM,
            ],
            strategy=RetrievalStrategy.HYBRID,
            depth=8,
            citation_required=True,
            memory_usage=True,
            external_search=False,
        )

    def assign_agents(self, tasks: list[ResearchTask]) -> dict[str, AgentType]:
        return {
            tasks[0].task_id: AgentType.RETRIEVER,
            tasks[1].task_id: AgentType.ANALYZER,
            tasks[2].task_id: AgentType.SUMMARIZER,
        }


class MethodologyStrategy(ResearchStrategy):
    strategy_type = ResearchStrategyType.METHODOLOGY

    def decompose(self, goal: ResearchGoal, keywords: list[str]) -> list[ResearchTask]:
        return [
            ResearchTask(
                task_id=f"mt_1_{goal.intent.value}",
                type=TaskType.LITERATURE_REVIEW,
                objective=f"Review existing methodologies: {goal.objective[:80]}",
                description=f"Survey existing methodologies and approaches for {', '.join(keywords[:6])}",
                expected_output="Methodology survey results",
                priority=8,
            ),
            ResearchTask(
                task_id=f"mt_2_{goal.intent.value}",
                type=TaskType.METHODOLOGY_DESIGN,
                objective=f"Design methodology: {goal.objective[:80]}",
                description="Design a structured research methodology based on survey findings",
                expected_output="Methodology specification document",
                priority=8,
            ),
        ]

    def create_dependencies(self, tasks: list[ResearchTask]) -> list[TaskDependency]:
        return [
            TaskDependency(task_id=tasks[1].task_id, depends_on=tasks[0].task_id, dependency_type=DependencyType.BLOCKING),
        ]

    def create_retrieval_plan(self, tasks: list[ResearchTask]) -> RetrievalPlan:
        return RetrievalPlan(
            collections=[
                SourceType.CHROMA_PAPER,
                SourceType.CHROMA_KNOWLEDGE,
                SourceType.MEMORY_PAPER,
                SourceType.MEMORY_PROJECT,
            ],
            strategy=RetrievalStrategy.HYBRID,
            depth=8,
            citation_required=True,
            memory_usage=True,
            external_search=False,
        )

    def assign_agents(self, tasks: list[ResearchTask]) -> dict[str, AgentType]:
        return {
            tasks[0].task_id: AgentType.RETRIEVER,
            tasks[1].task_id: AgentType.METHODOLOGY,
        }


class NoveltyInvestigationStrategy(ResearchStrategy):
    strategy_type = ResearchStrategyType.NOVELTY_INVESTIGATION

    def decompose(self, goal: ResearchGoal, keywords: list[str]) -> list[ResearchTask]:
        return [
            ResearchTask(
                task_id=f"nv_1_{goal.intent.value}",
                type=TaskType.LITERATURE_REVIEW,
                objective=f"Comprehensive literature review: {goal.objective[:80]}",
                description=f"Exhaustive search for related work on {', '.join(keywords[:6])}",
                expected_output="Exhaustive literature collection",
                priority=8,
            ),
            ResearchTask(
                task_id=f"nv_2_{goal.intent.value}",
                type=TaskType.PAPER_ANALYSIS,
                objective=f"Deep paper analysis: {goal.objective[:80]}",
                description="Deep analysis of all related papers for gaps and novelty",
                expected_output="Gap analysis report",
                priority=7,
            ),
            ResearchTask(
                task_id=f"nv_3_{goal.intent.value}",
                type=TaskType.COMPARISON,
                objective=f"Compare approaches: {goal.objective[:80]}",
                description="Compare existing approaches to identify novelty opportunities",
                expected_output="Novelty opportunity analysis",
                priority=6,
            ),
            ResearchTask(
                task_id=f"nv_4_{goal.intent.value}",
                type=TaskType.RESEARCH_SYNTHESIS,
                objective=f"Novelty report: {goal.objective[:80]}",
                description="Synthesize gap analysis and novelty opportunities",
                expected_output="Novelty investigation report",
                priority=4,
            ),
        ]

    def create_dependencies(self, tasks: list[ResearchTask]) -> list[TaskDependency]:
        return [
            TaskDependency(task_id=tasks[1].task_id, depends_on=tasks[0].task_id, dependency_type=DependencyType.BLOCKING),
            TaskDependency(task_id=tasks[2].task_id, depends_on=tasks[1].task_id, dependency_type=DependencyType.BLOCKING),
            TaskDependency(task_id=tasks[3].task_id, depends_on=tasks[2].task_id, dependency_type=DependencyType.BLOCKING),
        ]

    def create_retrieval_plan(self, tasks: list[ResearchTask]) -> RetrievalPlan:
        return RetrievalPlan(
            collections=[
                SourceType.CHROMA_PAPER,
                SourceType.CHROMA_CITATION,
                SourceType.CHROMA_KNOWLEDGE,
                SourceType.MEMORY_PAPER,
                SourceType.MEMORY_LONG_TERM,
            ],
            strategy=RetrievalStrategy.HYBRID,
            depth=15,
            citation_required=True,
            memory_usage=True,
            external_search=True,
        )

    def assign_agents(self, tasks: list[ResearchTask]) -> dict[str, AgentType]:
        return {
            tasks[0].task_id: AgentType.RETRIEVER,
            tasks[1].task_id: AgentType.ANALYZER,
            tasks[2].task_id: AgentType.ANALYZER,
            tasks[3].task_id: AgentType.SUMMARIZER,
        }


class GeneralStrategy(ResearchStrategy):
    strategy_type = ResearchStrategyType.GENERAL

    def decompose(self, goal: ResearchGoal, keywords: list[str]) -> list[ResearchTask]:
        return [
            ResearchTask(
                task_id=f"gn_1_{goal.intent.value}",
                type=TaskType.LITERATURE_REVIEW,
                objective=f"Search literature: {goal.objective[:80]}",
                description=f"Retrieve relevant information on {', '.join(keywords[:6])}",
                expected_output="Retrieved evidence",
                priority=7,
            ),
            ResearchTask(
                task_id=f"gn_2_{goal.intent.value}",
                type=TaskType.RESEARCH_SYNTHESIS,
                objective=f"Generate response: {goal.objective[:80]}",
                description="Synthesize retrieved information into answer",
                expected_output="Research output",
                priority=5,
            ),
        ]

    def create_dependencies(self, tasks: list[ResearchTask]) -> list[TaskDependency]:
        return [
            TaskDependency(task_id=tasks[1].task_id, depends_on=tasks[0].task_id, dependency_type=DependencyType.BLOCKING),
        ]

    def create_retrieval_plan(self, tasks: list[ResearchTask]) -> RetrievalPlan:
        return RetrievalPlan(
            collections=list(ALL_COLLECTIONS),
            strategy=RetrievalStrategy.HYBRID,
            depth=5,
            citation_required=False,
            memory_usage=True,
            external_search=False,
        )

    def assign_agents(self, tasks: list[ResearchTask]) -> dict[str, AgentType]:
        return {
            tasks[0].task_id: AgentType.RETRIEVER,
            tasks[1].task_id: AgentType.SUMMARIZER,
        }


_INTENT_STRATEGY_MAP: dict[SearchIntent, ResearchStrategyType] = {
    SearchIntent.FACTUAL: ResearchStrategyType.GENERAL,
    SearchIntent.EXPLORATORY: ResearchStrategyType.SURVEY,
    SearchIntent.COMPARATIVE: ResearchStrategyType.COMPARATIVE_ANALYSIS,
    SearchIntent.METHODOLOGICAL: ResearchStrategyType.METHODOLOGY,
    SearchIntent.CRITICAL: ResearchStrategyType.NOVELTY_INVESTIGATION,
    SearchIntent.SUMMARIZATION: ResearchStrategyType.GENERAL,
}

_STRATEGY_CLASSES: dict[ResearchStrategyType, type[ResearchStrategy]] = {
    ResearchStrategyType.LITERATURE_REVIEW: LiteratureReviewStrategy,
    ResearchStrategyType.COMPARATIVE_ANALYSIS: ComparativeAnalysisStrategy,
    ResearchStrategyType.EXPERIMENTAL: ExperimentalStrategy,
    ResearchStrategyType.SURVEY: SurveyStrategy,
    ResearchStrategyType.BENCHMARK: BenchmarkStrategy,
    ResearchStrategyType.METHODOLOGY: MethodologyStrategy,
    ResearchStrategyType.NOVELTY_INVESTIGATION: NoveltyInvestigationStrategy,
    ResearchStrategyType.GENERAL: GeneralStrategy,
}


class StrategySelector:
    def select(
        self,
        intent: SearchIntent,
        override: ResearchStrategyType | None = None,
        goal_analysis: ResearchGoal | None = None,
    ) -> ResearchStrategy:
        if override:
            st = override
        else:
            st = _INTENT_STRATEGY_MAP.get(intent, ResearchStrategyType.GENERAL)
            if st == ResearchStrategyType.GENERAL and goal_analysis:
                st = self._refine_from_complexity(goal_analysis, st)

        strategy_cls = _STRATEGY_CLASSES.get(st, GeneralStrategy)
        strategy = strategy_cls()
        logger.info(
            "strategy selected",
            extra={
                "intent": intent.value,
                "strategy": strategy.strategy_type.value,
                "override": override.value if override else None,
            },
        )
        return strategy

    def _refine_from_complexity(
        self,
        goal: ResearchGoal,
        current: ResearchStrategyType,
    ) -> ResearchStrategyType:
        if goal.complexity == TaskComplexity.COMPLEX and goal.estimated_difficulty >= 0.7:
            return ResearchStrategyType.EXPERIMENTAL
        if "comparison" in goal.required_outputs or "methodology" in goal.required_outputs:
            return ResearchStrategyType.COMPARATIVE_ANALYSIS
        return current
