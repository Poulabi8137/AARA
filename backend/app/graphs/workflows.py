from __future__ import annotations

from typing import Any

from app.graphs.research_graph import build_research_graph, ResearchWorkflow
from app.core.logging import get_logger

logger = get_logger("graphs.workflows")

__all__ = [
    "build_research_graph",
    "ResearchWorkflow",
    "run_research_workflow",
]


async def run_research_workflow(state: dict[str, Any]) -> dict[str, Any]:
    """Run the research workflow from a state dict.

    Extracts query, project_id, objective, and execution_id from the state,
    instantiates the workflow, and returns the final state.
    """
    workflow = ResearchWorkflow()
    query = state.get("query", "")
    project_id = state.get("project_id", "")
    objective = state.get("objective", "")
    execution_id = state.get("execution_id", "")

    logger.info(
        "running research workflow from state",
        extra={"query": query[:50] if query else ""},
    )
    return await workflow.arun(
        query=query,
        project_id=project_id,
        objective=objective,
        execution_id=execution_id,
    )
