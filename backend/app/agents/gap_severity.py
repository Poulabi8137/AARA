from __future__ import annotations

from typing import Any

from app.schemas.gap_detection import GapType, SeverityLevel


def compute_severity(
    gap_type: GapType,
    planner: dict[str, Any] | None,
    summary: dict[str, Any] | None = None,
) -> SeverityLevel:
    """Compute severity for a gap based on type, planner importance, and summary quality."""
    base = _base_severity(gap_type)
    modifier = _planner_importance_modifier(gap_type, planner)
    summary_mod = _summary_quality_modifier(gap_type, summary)

    score = base + modifier + summary_mod

    if score >= 8:
        return SeverityLevel.CRITICAL
    if score >= 5:
        return SeverityLevel.HIGH
    if score >= 3:
        return SeverityLevel.MEDIUM
    return SeverityLevel.LOW


def _base_severity(gap_type: GapType) -> int:
    mapping = {
        GapType.MISSING_SUBTOPIC: 5,
        GapType.LOW_EVIDENCE: 4,
        GapType.LOW_CITATION_COVERAGE: 3,
        GapType.CONTRADICTION: 6,
        GapType.OUTDATED_INFORMATION: 4,
        GapType.MISSING_RISK_ANALYSIS: 7,
        GapType.MISSING_PRIORITY_AREA: 6,
        GapType.MISSING_RESEARCH_QUESTION: 7,
        GapType.INSUFFICIENT_SOURCE_DIVERSITY: 3,
        GapType.LOW_CONFIDENCE_SUMMARY: 2,
    }
    return mapping.get(gap_type, 3)


def _planner_importance_modifier(
    gap_type: GapType, planner: dict[str, Any] | None
) -> int:
    if not planner:
        return 0
    modifier = 0
    if gap_type in (GapType.MISSING_SUBTOPIC, GapType.MISSING_RESEARCH_QUESTION):
        q_count = len(planner.get("research_questions", []))
        sub_count = len(planner.get("subtopics", []))
        if q_count >= 5 or sub_count >= 5:
            modifier = 1
    if gap_type in (GapType.MISSING_PRIORITY_AREA, GapType.MISSING_RISK_ANALYSIS):
        prio = planner.get("priority_areas", [])
        risks = planner.get("risk_areas", [])
        if len(prio) >= 3 or len(risks) >= 3:
            modifier = 2
    score = planner.get("planning_score", 50)
    if score >= 80:
        modifier += 1
    return modifier


def _summary_quality_modifier(gap_type: GapType, summary: dict[str, Any] | None) -> int:
    if not summary:
        return 0
    modifier = 0
    if gap_type == GapType.LOW_CONFIDENCE_SUMMARY:
        conf = summary.get("confidence_score", 50) or summary.get("summary_score", 50)
        if conf < 20:
            modifier = 2
        elif conf < 40:
            modifier = 1
    if gap_type == GapType.LOW_EVIDENCE:
        cites = summary.get("citation_count", 0)
        if cites == 0:
            modifier = 2
        elif cites < 3:
            modifier = 1
    if gap_type == GapType.CONTRADICTION:
        contra = summary.get("contradictions", [])
        if len(contra) >= 3:
            modifier = 2
        elif len(contra) >= 1:
            modifier = 1
    return modifier


def severity_sort_key(gap_type: GapType) -> int:
    """Numeric ordering for sorting gaps by severity priority."""
    return _base_severity(gap_type)
