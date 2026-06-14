from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Literal

from app.agents.state import ResearchState, make_initial_state
from app.graphs.nodes import (
    planner_node,
    retrieval_node,
    summarizer_node,
    gap_detection_node,
    report_generator_node,
)
from app.graphs.human_approval_node import human_approval_node
from app.core.logging import get_logger

logger = get_logger("graphs.research_graph")


class ResearchWorkflow:
    """Orchestrates the multi-agent research workflow.

    Uses LangGraph's StateGraph under the hood. This class is the
    public API that the agent router calls.
    """

    def __init__(self) -> None:
        self._graph = self._build()

    # ── Graph topology ────────────────────────────────────

    def _build(self):
        from langgraph.graph import StateGraph, END
        from langgraph.checkpoint.memory import MemorySaver

        builder = StateGraph(ResearchState)

        builder.add_node("planner", planner_node)
        builder.add_node("retrieval", retrieval_node)
        builder.add_node("summarizer", summarizer_node)
        builder.add_node("gap_detection", gap_detection_node)
        builder.add_node("report_generator", report_generator_node)
        builder.add_node("human_approval", human_approval_node)

        builder.set_entry_point("planner")
        builder.add_edge("planner", "retrieval")
        builder.add_edge("retrieval", "summarizer")
        builder.add_edge("summarizer", "gap_detection")
        builder.add_edge("gap_detection", "human_approval")
        builder.add_conditional_edges(
            "human_approval",
            self._route_from_approval,
            {
                "approved": "report_generator",
                "rejected": "report_generator",
                "rerun": "gap_detection",
                "skipped": "report_generator",
            },
        )

        builder.add_conditional_edges(
            "report_generator",
            self._should_continue,
            {
                "complete": END,
                "retry_planner": "planner",
                "retry_retrieval": "retrieval",
            },
        )

        checkpointer = MemorySaver()
        return builder.compile(checkpointer=checkpointer)

    @staticmethod
    def _should_continue(
        state: ResearchState,
    ) -> Literal["complete", "retry_planner", "retry_retrieval"]:
        """Conditional edge: decide if workflow is done or needs retry."""
        errors = state.get("errors", [])
        if errors and len(errors) < 3:
            if any("planner" in e for e in errors):
                return "retry_planner"
            if any("retrieval" in e for e in errors):
                return "retry_retrieval"
        return "complete"

    @staticmethod
    def _route_from_approval(state: ResearchState) -> str:
        approval_status = state.get("approval_status", "skipped")
        if approval_status == "rerun_requested":
            return "rerun"
        if approval_status == "rejected":
            return "rejected"
        return "approved"

    # ── Public API ────────────────────────────────────────

    async def arun(
        self,
        query: str,
        project_id: str = "",
        objective: str = "",
        thread_id: str | None = None,
        execution_id: str = "",
    ) -> dict[str, Any]:
        """Execute the full research workflow.

        Args:
            query: The research question or topic.
            project_id: Optional DB project ID for ownership.
            objective: Optional high-level research objective.
            thread_id: Optional LangGraph thread ID for checkpoint resume.
            execution_id: Optional execution ID for human approval tracking.

        Returns:
            Final ResearchState dict.
        """
        import uuid

        state = make_initial_state(
            query=query,
            project_id=project_id,
            objective=objective,
        )
        if execution_id:
            state["execution_id"] = execution_id

        if not query.strip():
            state["status"] = "failed"
            state["errors"] = ["query must not be empty"]
            logger.warning("workflow rejected: empty query")
            return dict(state)

        config = {
            "configurable": {
                "thread_id": thread_id or str(uuid.uuid4()),
            }
        }

        try:
            result = await self._graph.ainvoke(state, config)
            logger.info("workflow completed", extra={
                "thread_id": config["configurable"]["thread_id"],
                "status": result.get("status"),
            })
            return result
        except Exception as exc:
            logger.error("workflow failed", extra={"error": str(exc)})
            state["status"] = "failed"
            state["errors"] = [str(exc)]
            return dict(state)

    def get_graph(self):
        return self._graph


def build_research_graph() -> ResearchWorkflow:
    """Factory function."""
    return ResearchWorkflow()
