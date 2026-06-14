from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.agents.state import make_initial_state
from app.agents.gap_detection_agent import GapDetectionAgent
from app.agents.gap_analysis import detect_all_gaps, _parse_planner
from app.agents.gap_coverage import (
    compute_coverage_metrics,
    build_question_mapping,
    build_priority_mapping,
    build_risk_mapping,
)
from app.llm.mock_provider import MockProvider
from app.models.user import User
from app.schemas.gap_detection import CoverageMetrics, ResearchGap
from app.core.logging import get_logger
from app.services.auth_service import require_role
from app.models.user import UserRole

logger = get_logger("api.gap_debug")
router = APIRouter(tags=["Gap Detection Debug"])


class DebugGapRequest(BaseModel):
    planner_output: str | None = None
    summaries: list[dict[str, Any]] = []
    retrieved_documents: list[dict[str, Any]] = []
    query: str = "debug query"


class DebugGapResponse(BaseModel):
    gaps: list[dict[str, Any]]
    metrics: CoverageMetrics
    question_mapping: dict[str, str]
    priority_mapping: dict[str, str]
    risk_mapping: dict[str, str]
    gap_count: int
    severity_distribution: dict[str, int]
    total_gaps: int


@router.post("/gaps/debug", response_model=DebugGapResponse)
async def debug_gaps(
    body: DebugGapRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> DebugGapResponse:
    """Run gap detection on provided planner output, summaries, and bundles."""
    planner = _parse_planner(body.planner_output)

    gaps = detect_all_gaps(body.planner_output, body.summaries, body.retrieved_documents)
    metrics = compute_coverage_metrics(gaps, planner, body.summaries)

    question_mapping = build_question_mapping(
        planner.get("research_questions", []),
        body.summaries,
    )
    priority_mapping = build_priority_mapping(
        planner.get("priority_areas", []),
        body.summaries,
    )
    risk_mapping = build_risk_mapping(
        planner.get("risk_areas", []),
        body.summaries,
    )

    severity_distribution = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for g in gaps:
        sev = g.severity.value if hasattr(g.severity, "value") else str(g.severity)
        if sev in severity_distribution:
            severity_distribution[sev] += 1

    return DebugGapResponse(
        gaps=[g.model_dump() for g in gaps],
        metrics=metrics,
        question_mapping=question_mapping,
        priority_mapping=priority_mapping,
        risk_mapping=risk_mapping,
        gap_count=len(gaps),
        severity_distribution=severity_distribution,
        total_gaps=len(gaps),
    )
