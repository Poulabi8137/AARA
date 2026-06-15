from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict


class ResearchState(TypedDict, total=False):
    """Workflow state for the multi-agent research graph.

    Flows: planner -> retrieval -> summarizer -> gap_detection -> report_generator.
    Every field is optional so partial state can pass through any node.
    """

    project_id: str
    query: str
    objective: str

    planner_output: str | None
    retrieved_documents: list[dict[str, Any]]
    summaries: list[dict[str, Any]]
    research_gaps: list[dict[str, Any]]
    generated_report: str | None

    approval_status: str | None
    approval_data: dict[str, Any] | None

    execution_history: list[dict[str, Any]]
    agent_metrics: dict[str, Any]
    errors: list[str]
    status: str
    timestamp: str


def make_initial_state(
    query: str,
    project_id: str = "",
    objective: str = "",
) -> ResearchState:
    """Factory to build a fresh ResearchState with defaults."""
    now = datetime.now(timezone.utc).isoformat()
    return ResearchState(
        project_id=project_id,
        query=query,
        objective=objective,
        planner_output=None,
        retrieved_documents=[],
        summaries=[],
        research_gaps=[],
        generated_report=None,
        approval_status=None,
        approval_data=None,
        execution_history=[],
        agent_metrics={},
        errors=[],
        status="pending",
        timestamp=now,
    )
