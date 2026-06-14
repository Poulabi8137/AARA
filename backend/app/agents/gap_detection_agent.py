from __future__ import annotations

import time
from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry
from app.agents.state import ResearchState
from app.agents.gap_analysis import detect_all_gaps, _parse_planner
from app.agents.gap_coverage import (
    compute_coverage_metrics,
    build_question_mapping,
    build_priority_mapping,
    build_risk_mapping,
)
from app.schemas.gap_detection import (
    GapAnalysisResult,
    CoverageMetrics,
    ResearchGap,
)
from app.core.logging import get_logger

logger = get_logger("agents.gap_detection")


@AgentRegistry.register
class GapDetectionAgent(BaseAgent):
    agent_name = "gap_detection"
    description = "Identifies missing knowledge, weak evidence, unresolved contradictions, and research blind spots"
    requires_human_approval = False

    async def arun(self, state: ResearchState) -> ResearchState:
        start = time.monotonic()
        planner_raw = state.get("planner_output")
        summaries = state.get("summaries", [])
        bundles = state.get("retrieved_documents", [])

        planner = _parse_planner(planner_raw)

        if not summaries:
            logger.warning("no summaries available for gap detection, using fallback")
            gaps = self._fallback_gaps(planner, bundles)
            metrics = CoverageMetrics(total_gaps=len(gaps), used_fallback=True)
            question_mapping = {}
            priority_mapping = {}
            risk_mapping = {}
        else:
            gaps = detect_all_gaps(planner_raw, summaries, bundles)
            metrics = compute_coverage_metrics(gaps, planner, summaries)
            question_mapping = build_question_mapping(
                _list_from(planner, "research_questions"),
                summaries,
            )
            priority_mapping = build_priority_mapping(
                _list_from(planner, "priority_areas"),
                summaries,
            )
            risk_mapping = build_risk_mapping(
                _list_from(planner, "risk_areas"),
                summaries,
            )

        latency = round(time.monotonic() - start, 3)

        result = GapAnalysisResult(
            gaps=gaps,
            metrics=metrics,
            question_mapping=question_mapping,
            priority_mapping=priority_mapping,
            risk_mapping=risk_mapping,
            latency_seconds=latency,
            used_fallback=not bool(summaries),
        )

        state["research_gaps"] = [g.model_dump() for g in gaps]
        state["status"] = "gap_detection_complete"
        state["agent_metrics"]["gap_detection"] = result.model_dump()

        logger.info("gap detection complete", extra={
            "total_gaps": len(gaps),
            "coverage_score": metrics.coverage_score,
            "question_completion": metrics.question_completion_score,
            "risk_coverage": metrics.risk_coverage_score,
            "priority_coverage": metrics.priority_coverage_score,
            "latency": latency,
            "used_fallback": not bool(summaries),
        })

        return state

    def _fallback_gaps(
        self,
        planner: dict[str, Any],
        bundles: list[dict[str, Any]],
    ) -> list[ResearchGap]:
        """Generate basic gaps when no summaries are available."""
        from app.schemas.gap_detection import ResearchGap, GapType, SeverityLevel, RemediationSuggestion

        gaps: list[ResearchGap] = []
        if planner:
            subs = planner.get("subtopics", [])
            if subs:
                gaps.append(ResearchGap(
                    gap_id="fallback_no_summaries",
                    gap_type=GapType.LOW_EVIDENCE,
                    description="No summaries generated — all subtopics lack evidence synthesis",
                    severity=SeverityLevel.CRITICAL,
                    affected_subtopics=subs[:5],
                    supporting_evidence="Summariser produced no output; gap detection running in fallback mode",
                    remediation=RemediationSuggestion(
                        recommended_queries=planner.get("search_queries", [])[:3],
                        recommended_sources=["arxiv", "google scholar"],
                        recommended_actions=[
                            "Check summariser agent for errors",
                            "Verify retrieval pipeline produced bundles",
                            "Re-run workflow with debug logging enabled",
                        ],
                    ),
                    confidence=90.0,
                ))
        return gaps


def _list_from(planner: dict[str, Any], key: str) -> list[str]:
    raw = planner.get(key, [])
    if isinstance(raw, list):
        return [str(i).strip() for i in raw if i and str(i).strip()]
    return []
