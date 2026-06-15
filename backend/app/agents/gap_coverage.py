from __future__ import annotations

import re
from typing import Any

from app.schemas.gap_detection import CoverageMetrics, ResearchGap


def compute_coverage_metrics(
    gaps: list[ResearchGap],
    planner: dict[str, Any] | None,
    summaries: list[dict[str, Any]],
) -> CoverageMetrics:
    """Compute all coverage quality metrics from gaps, planner, and summaries."""
    subtopics_planned = _list_from(planner, "subtopics")
    questions_total = _list_from(planner, "research_questions")
    priority_areas = _list_from(planner, "priority_areas")
    risk_areas = _list_from(planner, "risk_areas")

    subtopics_covered = _covered_subtopics(summaries)
    questions_answered = _answered_questions(questions_total, summaries)
    priority_covered = _covered_priorities(priority_areas, summaries)
    risk_covered = _covered_risks(risk_areas, summaries)

    n_sub = len(subtopics_planned) or 1
    n_q = len(questions_total) or 1
    n_p = len(priority_areas) or 1
    n_r = len(risk_areas) or 1

    subtopic_rate = len(subtopics_covered) / n_sub
    question_rate = questions_answered / n_q
    priority_rate = priority_covered / n_p
    risk_rate = risk_covered / n_r

    avg_conf = _average_confidence(summaries)
    src_div = _source_diversity_score(summaries)

    raw_coverage = (
        subtopic_rate * 30.0 +
        question_rate * 30.0 +
        priority_rate * 15.0 +
        risk_rate * 15.0 +
        (avg_conf / 100.0) * 10.0
    ) * 100.0 / 85.0
    coverage_score = round(min(100.0, raw_coverage), 2)

    raw_completeness = (
        subtopic_rate * 25.0 +
        question_rate * 25.0 +
        priority_rate * 20.0 +
        risk_rate * 20.0 +
        (avg_conf / 100.0) * 10.0
    ) * 100.0 / 85.0
    completeness = round(min(100.0, raw_completeness), 2)

    severity_counts = _count_by_severity(gaps)

    return CoverageMetrics(
        coverage_score=coverage_score,
        question_completion_score=round(question_rate * 100, 2),
        risk_coverage_score=round(risk_rate * 100, 2),
        priority_coverage_score=round(priority_rate * 100, 2),
        research_completeness_score=completeness,
        source_diversity_score=round(src_div, 2),
        average_confidence_score=round(avg_conf, 2),
        total_gaps=len(gaps),
        critical_gaps=severity_counts["critical"],
        high_gaps=severity_counts["high"],
        medium_gaps=severity_counts["medium"],
        low_gaps=severity_counts["low"],
        subtopics_planned=len(subtopics_planned),
        subtopics_covered=len(subtopics_covered),
        questions_total=len(questions_total),
        questions_answered=questions_answered,
        priority_areas_total=len(priority_areas),
        priority_areas_covered=priority_covered,
        risk_areas_total=len(risk_areas),
        risk_areas_covered=risk_covered,
    )


def build_question_mapping(
    questions: list[str],
    summaries: list[dict[str, Any]],
) -> dict[str, str]:
    """Map each research question to its coverage status."""
    mapping: dict[str, str] = {}
    for q in questions:
        q_lower = q.lower()
        tokens = set(re.findall(r"\b[a-zA-Z]{4,}\b", q_lower))
        found = False
        for s in summaries:
            text = _summary_text(s).lower()
            overlap = sum(1 for t in tokens if t in text)
            if overlap >= max(2, len(tokens) // 2):
                mapping[q] = "covered"
                found = True
                break
        if not found:
            mapping[q] = "uncovered"
    return mapping


def build_priority_mapping(
    priorities: list[str],
    summaries: list[dict[str, Any]],
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for p in priorities:
        p_lower = p.lower()
        tokens = set(re.findall(r"\b[a-zA-Z]{4,}\b", p_lower))
        found = False
        for s in summaries:
            text = _summary_text(s).lower()
            overlap = sum(1 for t in tokens if t in text)
            if overlap >= max(1, len(tokens) // 3):
                mapping[p] = "covered"
                found = True
                break
        if not found:
            mapping[p] = "uncovered"
    return mapping


def build_risk_mapping(
    risks: list[str],
    summaries: list[dict[str, Any]],
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for r in risks:
        r_lower = r.lower()
        tokens = set(re.findall(r"\b[a-zA-Z]{4,}\b", r_lower))
        found = False
        for s in summaries:
            text = _summary_text(s).lower()
            overlap = sum(1 for t in tokens if t in text)
            if overlap >= max(1, len(tokens) // 3):
                mapping[r] = "covered"
                found = True
                break
        if not found:
            mapping[r] = "uncovered"
    return mapping


# ── Internal helpers ────────────────────────────────────


def _list_from(planner: dict[str, Any] | None, key: str) -> list[str]:
    if not planner:
        return []
    raw = planner.get(key, [])
    if isinstance(raw, list):
        return raw
    return []


def _covered_subtopics(summaries: list[dict[str, Any]]) -> set[str]:
    covered: set[str] = set()
    for s in summaries:
        sub = s.get("subtopic", "")
        if sub:
            covered.add(sub.lower().strip())
        kf = s.get("key_findings", [])
        if kf:
            for f in kf:
                covered.add(f.lower().strip()[:40])
    return covered


def _answered_questions(questions: list[str], summaries: list[dict[str, Any]]) -> int:
    mapping = build_question_mapping(questions, summaries)
    return sum(1 for v in mapping.values() if v == "covered")


def _covered_priorities(priorities: list[str], summaries: list[dict[str, Any]]) -> int:
    mapping = build_priority_mapping(priorities, summaries)
    return sum(1 for v in mapping.values() if v == "covered")


def _covered_risks(risks: list[str], summaries: list[dict[str, Any]]) -> int:
    mapping = build_risk_mapping(risks, summaries)
    return sum(1 for v in mapping.values() if v == "covered")


def _summary_text(summary: dict[str, Any]) -> str:
    parts = [
        summary.get("executive_summary", ""),
        " ".join(summary.get("key_findings", [])),
        " ".join(summary.get("supporting_evidence", [])),
        " ".join(summary.get("consensus_points", [])),
        " ".join(summary.get("important_statistics", [])),
    ]
    return " ".join(p for p in parts if p)


def _average_confidence(summaries: list[dict[str, Any]]) -> float:
    if not summaries:
        return 0.0
    scores = [s.get("confidence_score", 0) or s.get("summary_score", 0) for s in summaries]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def _source_diversity_score(summaries: list[dict[str, Any]]) -> float:
    if not summaries:
        return 0.0
    total_citations = 0
    for s in summaries:
        s.get("source_count", 0)
        cites = s.get("citation_count", 0)
        total_citations += cites
    unique_sources = sum(s.get("source_count", 0) for s in summaries)
    if total_citations == 0:
        return 0.0
    ratio = min(1.0, unique_sources / max(total_citations, 1))
    return ratio * 100.0


def _count_by_severity(gaps: list[ResearchGap]) -> dict[str, int]:
    counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for g in gaps:
        sev = g.severity.value if hasattr(g.severity, "value") else str(g.severity)
        if sev in counts:
            counts[sev] += 1
    return counts
