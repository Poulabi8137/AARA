from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.agents.state import make_initial_state
from app.agents.summarizer_agent import SummarizerAgent
from app.llm.mock_provider import MockProvider
from app.models.user import User
from app.core.logging import get_logger
from app.services.auth_service import require_role
from app.models.user import UserRole

logger = get_logger("api.summarizer_debug")
router = APIRouter(tags=["Summarizer Debug"])


class DebugSummarizerRequest(BaseModel):
    retrieved_documents: list[dict[str, Any]] = []
    query: str = "debug query"


class DebugSummarizerResponse(BaseModel):
    summaries: list[dict[str, Any]]
    metrics: dict[str, Any]
    total_sections: int
    total_citations: int
    average_score: float


@router.post("/summaries/debug", response_model=DebugSummarizerResponse)
async def debug_summarizer(
    body: DebugSummarizerRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> DebugSummarizerResponse:
    """Run the summarizer pipeline on provided bundles."""
    provider = MockProvider()
    agent = SummarizerAgent(llm_provider=provider)
    state = make_initial_state(query=body.query)
    state["retrieved_documents"] = body.retrieved_documents or []

    await agent.run(state)

    summaries_raw = state.get("summaries", [])
    metrics_raw = state.get("agent_metrics", {}).get("summarizer", {})

    total_citations = sum(s.get("citation_count", 0) for s in summaries_raw)
    scores = [s.get("summary_score", 0) for s in summaries_raw]
    avg_score = round(sum(scores) / max(len(scores), 1), 2) if scores else 0.0

    return DebugSummarizerResponse(
        summaries=summaries_raw,
        metrics=metrics_raw,
        total_sections=len(summaries_raw),
        total_citations=total_citations,
        average_score=avg_score,
    )
