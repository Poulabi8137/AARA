from __future__ import annotations

from typing import Any

from app.evaluation.metrics import (
    compute_citation_density,
    compute_evidence_strength,
    compute_gap_coverage,
    compute_hallucination_proxy,
    compute_question_coverage,
    compute_report_completeness,
    compute_research_quality,
    compute_source_diversity,
    compute_summary_quality,
)


def generate_scorecard(state: dict[str, Any]) -> dict[str, Any]:
    """Run all metrics on a ResearchState and return a structured scorecard.

    Args:
        state: ResearchState dict from a workflow execution.

    Returns:
        dict with:
        - scores: dict of metric_name -> score (0-100)
        - details: optional breakdown per metric
        - composite: research_quality_score (0-100)
        - summary: tier label + pass/fail
    """
    planner_output = state.get("planner_output", "")
    summaries: list[dict[str, Any]] = state.get("summaries", [])
    gaps: list[dict[str, Any]] = state.get("research_gaps", [])
    report: dict[str, Any] | None = _safe_parse_report(state.get("generated_report"))
    sections: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []
    sources: list[str] = []
    key_findings: list[str] = []
    evidence_chunks: list[dict[str, Any]] = []
    planner_questions: list[str] = []
    answered_questions: list[str] = []

    for s in summaries:
        sec_citations = s.get("citations", [])
        if isinstance(sec_citations, list):
            citations.extend(sec_citations)
        sec_sources = s.get("sources", [])
        if isinstance(sec_sources, list):
            sources.extend(sec_sources)
        findings = s.get("key_findings", [])
        if isinstance(findings, list):
            key_findings.extend(findings)
        evidence = s.get("supporting_evidence", [])
        if isinstance(evidence, list):
            for ev in evidence:
                if isinstance(ev, dict):
                    evidence_chunks.append(ev)
                elif isinstance(ev, str):
                    evidence_chunks.append({"content": ev})

    if report:
        sections = report.get("sections", [])

    try:
        import json
        po = json.loads(planner_output) if isinstance(planner_output, str) else {}
        planner_questions = po.get("research_questions", [])
    except (json.JSONDecodeError, TypeError, ValueError):
        planner_questions = []

    answered_questions = [
        s.get("subtopic", "") for s in summaries if s.get("subtopic")
    ]


    scores: dict[str, float] = {}
    details: dict[str, Any] = {}

    scores["question_coverage"] = compute_question_coverage(
        planner_questions, answered_questions, summaries
    )
    details["question_coverage"] = {
        "planner_questions": len(planner_questions),
        "answered_questions": len(answered_questions),
        "matched": planner_questions
        if len(planner_questions) <= 5
        else f"{len(planner_questions)} questions",
    }

    scores["citation_density"] = compute_citation_density(citations, sections)
    details["citation_density"] = {
        "total_citations": len(citations),
        "total_sections": max(len(sections), 1),
    }

    scores["source_diversity"] = compute_source_diversity(sources, citations)
    details["source_diversity"] = {
        "unique_sources": len(set(sources)),
        "total_citations": len(citations),
    }

    scores["evidence_strength"] = compute_evidence_strength(evidence_chunks, key_findings)
    details["evidence_strength"] = {
        "evidence_chunks": len(evidence_chunks),
        "key_findings": len(key_findings),
    }

    scores["summary_quality"] = compute_summary_quality(summaries)
    details["summary_quality"] = {
        "summaries_count": len(summaries),
    }

    scores["gap_coverage"] = compute_gap_coverage(gaps)
    details["gap_coverage"] = {
        "total_gaps": len(gaps),
    }

    scores["report_completeness"] = compute_report_completeness(report, sections)
    details["report_completeness"] = {
        "report_exists": report is not None,
        "sections_count": len(sections),
    }

    scores["hallucination_risk"] = compute_hallucination_proxy(
        report, sections, citations, key_findings
    )
    details["hallucination_risk"] = {
        "total_key_findings": len(key_findings),
    }

    scores["research_quality"] = compute_research_quality(
        question_coverage=scores["question_coverage"],
        citation_density=scores["citation_density"],
        source_diversity=scores["source_diversity"],
        evidence_strength=scores["evidence_strength"],
        summary_quality=scores["summary_quality"],
        gap_coverage=scores["gap_coverage"],
        report_completeness=scores["report_completeness"],
        hallucination_risk=scores["hallucination_risk"],
    )

    q = scores["research_quality"]
    if q >= 80:
        tier = "excellent"
    elif q >= 60:
        tier = "good"
    elif q >= 40:
        tier = "acceptable"
    else:
        tier = "poor"

    return {
        "scores": scores,
        "details": details,
        "composite": scores["research_quality"],
        "summary": {
            "tier": tier,
            "passed": q >= 60,
            "total_metrics": len(scores),
        },
    }


def _safe_parse_report(report_data: Any) -> dict[str, Any] | None:
    if report_data is None:
        return None
    if isinstance(report_data, dict):
        return report_data
    if isinstance(report_data, str):
        try:
            import json
            return json.loads(report_data)
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
    return None
