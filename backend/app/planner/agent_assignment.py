from __future__ import annotations

from app.core.logging import get_logger
from app.planner.models import AgentType, ExecutionStep, ResearchTask, TaskStatus, TaskType

logger = get_logger("planner.agent_assignment")

_TASK_AGENT_MAP: dict[TaskType, AgentType] = {
    TaskType.LITERATURE_REVIEW: AgentType.RETRIEVER,
    TaskType.SURVEY: AgentType.RETRIEVER,
    TaskType.COMPARISON: AgentType.ANALYZER,
    TaskType.EXPERIMENT_PLANNING: AgentType.EXPERIMENT,
    TaskType.BENCHMARK_ANALYSIS: AgentType.ANALYZER,
    TaskType.DATASET_DISCOVERY: AgentType.RETRIEVER,
    TaskType.PAPER_ANALYSIS: AgentType.ANALYZER,
    TaskType.RESEARCH_SYNTHESIS: AgentType.SUMMARIZER,
    TaskType.METHODOLOGY_DESIGN: AgentType.METHODOLOGY,
}


class AgentAssigner:
    def assign(self, tasks: list[ResearchTask]) -> list[ExecutionStep]:
        steps: list[ExecutionStep] = []
        for task in tasks:
            agent = _TASK_AGENT_MAP.get(task.type, AgentType.RETRIEVER)
            step = ExecutionStep(
                task_id=task.task_id,
                agent_type=agent,
                task_type=task.type,
                objective=task.objective,
                priority=task.priority,
                status=TaskStatus(task.status.value),
            )
            task.assigned_agent = agent
            steps.append(step)

        logger.info(
            "agent assignment complete",
            extra={
                "step_count": len(steps),
                "agent_types": list({s.agent_type.value for s in steps}),
            },
        )
        return steps
