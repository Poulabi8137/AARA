from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.agents.state import make_initial_state
from app.agents.retrieval_agent import RetrievalAgent
from app.llm.mock_provider import MockProvider
from app.models.user import User
from app.core.logging import get_logger
from app.services.auth_service import require_role
from app.models.user import UserRole

logger = get_logger("api.retrieval_debug")
router = APIRouter(tags=["Retrieval Debug"])


class DebugRetrievalRequest(BaseModel):
    query: str = ""
    planner_output_json: str = ""
    project_id: str = ""


class DebugRetrievalResponse(BaseModel):
    debug: dict[str, Any]
    metrics: dict[str, Any]
    bundles: list[dict[str, Any]]
    total_evidence_chunks: int


@router.post("/retrieval/debug", response_model=DebugRetrievalResponse)
async def debug_retrieval(
    body: DebugRetrievalRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> DebugRetrievalResponse:
    """Run the full retrieval pipeline and return debug telemetry."""
    provider = MockProvider()
    agent = RetrievalAgent(llm_provider=provider)

    query = body.query or "test debug query"
    state = make_initial_state(query=query, project_id=body.project_id)

    if body.planner_output_json:
        try:
            parsed = json.loads(body.planner_output_json)
            state["planner_output"] = body.planner_output_json
            if not body.query and parsed.get("search_queries"):
                state["query"] = parsed["search_queries"][0]
        except json.JSONDecodeError:
            logger.warning("invalid planner_output_json in debug request")

    await agent.run(state)

    bundles_raw = state.get("retrieved_documents", [])
    metrics_raw = state.get("agent_metrics", {}).get("retrieval", {})
    debug_raw = state.get("agent_metrics", {}).get("retrieval_debug", {})

    total = sum(len(b.get("evidence", [])) for b in bundles_raw)

    return DebugRetrievalResponse(
        debug=debug_raw,
        metrics=metrics_raw,
        bundles=bundles_raw,
        total_evidence_chunks=total,
    )
