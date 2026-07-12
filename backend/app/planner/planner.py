from __future__ import annotations

import time
import uuid
from typing import Any

from app.core.logging import get_logger
from app.planner.agent_assignment import AgentAssigner
from app.planner.config import get_planner_settings
from app.planner.dependency_graph import DependencyGraphBuilder
from app.planner.goal_analyzer import GoalAnalyzer
from app.planner.models import (
    ExecutionPlan,
    ExecutionStep,
    PlanningContext,
    PlanningMetadata,
    PlanningResult,
    ResearchStrategyType,
    ResearchTask,
    TaskDependency,
)
from app.planner.retrieval_planner import RetrievalPlanner
from app.planner.strategies import StrategySelector
from app.planner.task_decomposer import TaskDecomposer
from app.planner.validator import PlanValidator
from app.rag.query_processor import QueryProcessor
from app.services.research_memory.manager import ResearchMemoryManager

logger = get_logger("planner.orchestrator")
settings = get_planner_settings()


class Planner:
    def __init__(
        self,
        query_processor: QueryProcessor | None = None,
        memory_manager: ResearchMemoryManager | None = None,
        goal_analyzer: GoalAnalyzer | None = None,
        task_decomposer: TaskDecomposer | None = None,
        dependency_builder: DependencyGraphBuilder | None = None,
        retrieval_planner: RetrievalPlanner | None = None,
        agent_assigner: AgentAssigner | None = None,
        strategy_selector: StrategySelector | None = None,
        validator: PlanValidator | None = None,
    ):
        self._qp = query_processor or QueryProcessor()
        self._memory = memory_manager
        self._goal_analyzer = goal_analyzer or GoalAnalyzer(self._qp)
        self._task_decomposer = task_decomposer or TaskDecomposer()
        self._dependency_builder = dependency_builder or DependencyGraphBuilder()
        self._retrieval_planner = retrieval_planner or RetrievalPlanner()
        self._agent_assigner = agent_assigner or AgentAssigner()
        self._strategy_selector = strategy_selector or StrategySelector()
        self._validator = validator or PlanValidator()

    async def plan(
        self,
        query: str,
        user_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        strategy_override: ResearchStrategyType | None = None,
    ) -> PlanningResult:
        start = time.monotonic()

        goal, intent = self._goal_analyzer.analyze(
            query=query,
            user_id=user_id,
            project_id=project_id,
        )

        context = PlanningContext(
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
            previous_plans=await self._load_previous_plans(user_id, project_id),
        )

        pq = self._qp.process(
            query=query,
            user_id=user_id,
            project_id=project_id,
        )

        strategy = self._strategy_selector.select(
            intent=goal.intent,
            override=strategy_override,
            goal_analysis=goal,
        )
        strategy_type = strategy.strategy_type

        tasks = strategy.decompose(goal, pq.keywords)
        custom_deps = strategy.create_dependencies(tasks)
        retrieval_plan = strategy.create_retrieval_plan(tasks)
        agent_map = strategy.assign_agents(tasks)

        self._sync_task_dependencies(tasks, custom_deps)
        self._attach_retrieval_plans(tasks, retrieval_plan)
        self._attach_agent_assignments(tasks, agent_map)

        graph = self._dependency_builder.build(tasks, custom_deps)

        steps: list[ExecutionStep] = []
        for task in tasks:
            agent_type = agent_map.get(task.task_id, task.assigned_agent)
            steps.append(
                ExecutionStep(
                    task_id=task.task_id,
                    agent_type=agent_type or list(agent_map.values())[0],
                    task_type=task.type,
                    objective=task.objective,
                    priority=task.priority,
                )
            )

        plan_id = f"plan_{uuid.uuid4().hex[:12]}"
        execution_plan = ExecutionPlan(
            plan_id=plan_id,
            goal=goal,
            tasks=tasks,
            dependencies=custom_deps,
            dependency_graph=graph,
            steps=steps,
            strategy=strategy_type,
            context=context,
        )

        validation = self._validator.validate(execution_plan)
        duration = time.monotonic() - start

        metadata = PlanningMetadata(
            duration_ms=round(duration * 1000, 1),
            strategy_used=strategy_type,
            validation_passed=validation.is_valid,
            validation_errors=validation.errors,
        )
        execution_plan.metadata = metadata

        logger.info(
            "planning complete",
            extra={
                "plan_id": plan_id,
                "strategy": strategy_type.value,
                "tasks": len(tasks),
                "steps": len(steps),
                "valid": validation.is_valid,
                "duration_ms": metadata.duration_ms,
            },
        )

        return PlanningResult(
            plan=execution_plan,
            validation=validation,
            metadata=metadata,
        )

    def _sync_task_dependencies(
        self,
        tasks: list[ResearchTask],
        custom_deps: list[TaskDependency],
    ) -> None:
        task_map = {t.task_id: t for t in tasks}
        for dep in custom_deps:
            task = task_map.get(dep.task_id)
            if task and dep.depends_on not in task.dependencies:
                task.dependencies.append(dep.depends_on)

    def _attach_retrieval_plans(
        self,
        tasks: list[ResearchTask],
        plan: Any,
    ) -> None:
        for task in tasks:
            task.retrieval_plan = plan

    def _attach_agent_assignments(
        self,
        tasks: list[ResearchTask],
        agent_map: dict[str, Any],
    ) -> None:
        for task in tasks:
            task.assigned_agent = agent_map.get(task.task_id)

    async def _load_previous_plans(
        self,
        user_id: uuid.UUID | None,
        project_id: uuid.UUID | None,
    ) -> list[str]:
        if not self._memory or not settings.enable_memory_lookup:
            return []
        try:
            result = await self._memory.search(
                query="previous research plans",
                user_id=user_id,
                top_k=3,
                memory_types=None,
            )
            return [f"plan_{hit.memory_id}" for hit in result.results]
        except Exception as exc:
            logger.debug("memory lookup failed", extra={"error": str(exc)})
            return []
