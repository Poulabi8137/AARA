from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.agents.state import ResearchState
from app.core.config import get_settings
from app.core.logging import get_logger
from app.llm.factory import get_llm_provider

logger = get_logger("graphs.nodes")

_settings = get_settings()
_provider = get_llm_provider(_settings)


def _record_execution(state: ResearchState, node_name: str) -> None:
    """Append a step to execution_history."""
    history = state.get("execution_history", [])
    history.append({
        "node": node_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": state.get("status", "unknown"),
    })
    state["execution_history"] = history


async def planner_node(state: ResearchState) -> dict[str, Any]:
    """Planner: produces a research plan using PlannerAgent."""
    logger.info("planner_node: starting", extra={"query": state.get("query", "")})
    _record_execution(state, "planner")

    from app.agents.planner_agent import PlannerAgent

    agent = PlannerAgent(llm_provider=_provider)
    result = await agent.run(state)
    if not result.success:
        logger.warning("planner_node completed with errors", extra={"error": result.error})

    state["status"] = "planner_complete"
    return state


async def retrieval_node(state: ResearchState) -> dict[str, Any]:
    """Retrieval: multi-collection search with ranking, dedup, bundling."""
    logger.info("retrieval_node: starting")
    _record_execution(state, "retrieval")

    from app.agents.retrieval_agent import RetrievalAgent

    agent = RetrievalAgent(llm_provider=_provider)
    result = await agent.run(state)
    if not result.success:
        logger.warning("retrieval_node completed with errors", extra={"error": result.error})

    state["status"] = "retrieval_complete"
    return state


async def summarizer_node(state: ResearchState) -> dict[str, Any]:
    """Summarizer: transforms retrieval bundles into evidence-grounded section summaries."""
    logger.info("summarizer_node: starting")
    _record_execution(state, "summarizer")

    from app.agents.summarizer_agent import SummarizerAgent

    agent = SummarizerAgent(llm_provider=_provider)
    result = await agent.run(state)
    if not result.success:
        logger.warning("summarizer_node completed with errors", extra={"error": result.error})

    state["status"] = "summarizer_complete"
    return state


async def gap_detection_node(state: ResearchState) -> dict[str, Any]:
    """Gap Detection: identifies missing information using GapDetectionAgent."""
    logger.info("gap_detection_node: starting")
    _record_execution(state, "gap_detection")

    from app.agents.gap_detection_agent import GapDetectionAgent

    agent = GapDetectionAgent(llm_provider=_provider)
    result = await agent.run(state)
    if not result.success:
        logger.warning("gap_detection_node completed with errors", extra={"error": result.error})

    state["status"] = "gap_detection_complete"
    return state


async def report_generator_node(state: ResearchState) -> dict[str, Any]:
    """Report Generator: produces publication-quality research report using ReportGeneratorAgent."""
    logger.info("report_generator_node: starting")
    _record_execution(state, "report_generator")

    from app.agents.report_generator_agent import ReportGeneratorAgent

    agent = ReportGeneratorAgent(llm_provider=_provider)
    result = await agent.run(state)
    if not result.success:
        logger.warning("report_generator_node completed with errors", extra={"error": result.error})

    state["status"] = "report_generation_complete"
    return state
