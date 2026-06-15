from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.schemas.report_generator import (
    ReportSection,
    ReportCitation,
    ReportContradiction,
    ResearchReport,
)
from app.agents.report_references import (
    aggregate_references,
    build_citation_list,
    build_contradiction_list,
)
from app.agents.report_scoring import compute_report_quality
from app.agents.report_validation import validate_report_data


def build_markdown(report: ResearchReport) -> str:
    """Generate publication-quality markdown from a ResearchReport."""
    lines: list[str] = []

    # Title
    lines.append(f"# {report.title}")
    lines.append("")
    lines.append(f"*Generated: {report.generated_at}*")
    lines.append("")

    # Quality badge
    q = report.metrics.research_quality_score
    badge = "🟢 Excellent" if q >= 80 else "🟡 Good" if q >= 60 else "🟠 Fair" if q >= 40 else "🔴 Needs Improvement"
    lines.append(f"> **Quality Assessment**: {badge} ({q:.1f}/100)")
    lines.append("")

    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(report.executive_summary)
    lines.append("")

    # Introduction
    lines.append("## Introduction")
    lines.append("")
    lines.append(report.introduction)
    lines.append("")

    # Research Objectives
    if report.research_objectives:
        lines.append("## Research Objectives")
        lines.append("")
        for obj in report.research_objectives:
            lines.append(f"- {obj}")
        lines.append("")

    # Methodology
    lines.append("## Methodology")
    lines.append("")
    lines.append(report.methodology)
    lines.append("")

    # Findings by Subtopic
    if report.sections:
        lines.append("## Findings by Subtopic")
        lines.append("")
        for i, sec in enumerate(report.sections, 1):
            _render_section(lines, sec, i)
        lines.append("")

    # Key Findings (aggregated)
    if report.key_findings:
        lines.append("## Key Findings")
        lines.append("")
        for f in report.key_findings:
            lines.append(f"- {f}")
        lines.append("")

    # Contradictions
    if report.contradictions:
        lines.append("## Contradictions and Conflicting Evidence")
        lines.append("")
        for c in report.contradictions:
            lines.append(f"### {c.topic}")
            lines.append(f"*Subtopic: {c.subtopic} | Severity: {c.severity}*")
            for stmt in c.statements:
                lines.append(f"- {stmt}")
            lines.append("")

    # Research Gaps
    if report.research_gaps:
        lines.append("## Research Gaps")
        lines.append("")
        _render_gaps(lines, report.research_gaps)
        lines.append("")

    # Limitations
    if report.limitations:
        lines.append("## Limitations")
        lines.append("")
        for lim in report.limitations:
            lines.append(f"- {lim}")
        lines.append("")

    # Recommendations
    if report.recommendations:
        lines.append("## Recommendations")
        lines.append("")
        for rec in report.recommendations:
            lines.append(f"- {rec}")
        lines.append("")

    # Future Research
    if report.future_research:
        lines.append("## Future Research Directions")
        lines.append("")
        for fr in report.future_research:
            lines.append(f"- {fr}")
        lines.append("")

    # Conclusion
    lines.append("## Conclusion")
    lines.append("")
    lines.append(report.conclusion)
    lines.append("")

    # References
    if report.references:
        lines.append("## References")
        lines.append("")
        for ref in report.references:
            lines.append(f"[{ref.reference_id}] {ref.source}")
            if ref.claims:
                claims_text = "; ".join(ref.claims[:2])
                lines.append(f"    → {claims_text}")
            lines.append(f"    *Cited in: {', '.join(ref.subtopics)} | Occurrences: {ref.occurrence_count}*")
            lines.append("")

    # Metrics summary
    lines.append("---")
    lines.append(f"*Report metrics: {report.metrics.section_count} sections, "
                 f"{report.metrics.reference_count} references, "
                 f"{report.metrics.citation_count} citations, "
                 f"{report.metrics.report_length} characters*")

    return "\n".join(lines)


def build_json(report: ResearchReport) -> str:
    """Serialize report to pretty-printed JSON."""
    return json.dumps(report.model_dump(), indent=2, default=str)


def build_report_from_state(
    query: str,
    planner_raw: str | None,
    summaries: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
    objective: str = "",
) -> ResearchReport:
    """Build a complete ResearchReport from ResearchState data."""
    start = datetime.now(timezone.utc)

    planner = _parse_planner(planner_raw)
    sections = _build_report_sections(summaries)
    references = aggregate_references(summaries)
    build_citation_list(summaries)
    contradictions = build_contradiction_list(summaries)

    # Key findings (aggregated from all sections)
    key_findings = _aggregate_key_findings(summaries)

    # Introduction from planner or default
    research_goal = planner.get("research_goal", "") if planner else ""
    introduction = _build_introduction(query, research_goal, planner)

    # Methodology
    methodology = _build_methodology(planner)

    # Research objectives
    research_objectives = planner.get("research_questions", []) if planner else []

    # Limitations, recommendations, future research from gaps
    limitations = _extract_limitations(gaps)
    recommendations = _extract_recommendations(gaps)
    future_research = _extract_future_research(gaps)

    # Executive summary
    executive_summary = _build_executive_summary(query, sections, gaps, key_findings)

    # Conclusion
    conclusion = _build_conclusion(query, sections, gaps)

    # Metrics
    metrics = compute_report_quality(
        [s.model_dump() for s in sections],
        [r.model_dump() for r in references],
        gaps,
    )

    now = datetime.now(timezone.utc).isoformat()
    title = f"Research Report: {query}"

    report = ResearchReport(
        title=title,
        query=query,
        executive_summary=executive_summary,
        introduction=introduction,
        research_objectives=research_objectives,
        methodology=methodology,
        sections=sections,
        key_findings=key_findings,
        contradictions=contradictions,
        research_gaps=gaps,
        limitations=limitations,
        recommendations=recommendations,
        future_research=future_research,
        conclusion=conclusion,
        references=references,
        metrics=metrics,
        generated_at=now,
    )

    # Validate before formatting
    validation = validate_report_data(
        query,
        [s.model_dump() for s in sections],
        [r.model_dump() for r in references],
        conclusion,
    )
    if validation.errors:
        report.metrics.report_completeness = max(
            0.0, report.metrics.report_completeness - len(validation.errors) * 10.0
        )

    # Generate formatted outputs
    report.markdown = build_markdown(report)
    report.report_json = build_json(report)
    report.metrics.report_length = len(report.markdown)
    report.metrics.generation_latency = round(
        (datetime.now(timezone.utc) - start).total_seconds(), 3
    )

    return report


# ── Internal helpers ────────────────────────────────────


def _render_section(lines: list[str], sec: ReportSection, index: int) -> None:
    lines.append(f"### {index}. {sec.title}")
    lines.append("")
    conf = sec.confidence_score
    badge = "High" if conf >= 70 else "Medium" if conf >= 40 else "Low"
    lines.append(f"*Confidence: {badge} ({conf:.1f}/100) | "
                 f"Citations: {sec.citation_count} | Sources: {sec.source_count}*")
    lines.append("")
    lines.append(sec.summary)
    lines.append("")

    if sec.key_findings:
        lines.append("**Key Findings:**")
        for f in sec.key_findings:
            lines.append(f"- {f}")
        lines.append("")

    if sec.evidence_highlights:
        lines.append("**Evidence Highlights:**")
        for e in sec.evidence_highlights[:3]:
            lines.append(f"- {e}")
        lines.append("")

    if sec.statistics:
        lines.append("**Key Statistics:**")
        for st in sec.statistics[:5]:
            lines.append(f"- {st}")
        lines.append("")

    if sec.citations:
        lines.append("**Sources:**")
        for c in sec.citations[:5]:
            lines.append(f"- {c.source}: {c.claim[:100]}")
        lines.append("")


def _render_gaps(lines: list[str], gaps: list[dict[str, Any]]) -> None:
    for g in gaps:
        gap_type = g.get("gap_type", "GAP")
        sev = g.get("severity", "unknown")
        desc = g.get("description", "")
        confidence = g.get("confidence", 0)
        sev_label = sev.upper() if isinstance(sev, str) else "UNKNOWN"

        lines.append(f"**[{sev_label}] ({gap_type})**")
        lines.append(f"  {desc}")
        if confidence:
            lines.append(f"  *Confidence: {confidence:.0f}%*")

        remediation = g.get("remediation", {})
        if isinstance(remediation, dict):
            queries = remediation.get("recommended_queries", [])
            actions = remediation.get("recommended_actions", [])
            if queries:
                lines.append("  Recommended searches:")
                for q in queries[:3]:
                    lines.append(f"  - `{q}`")
            if actions:
                lines.append("  Recommended actions:")
                for a in actions[:3]:
                    lines.append(f"  - {a}")
        lines.append("")


def _parse_planner(planner_raw: str | None) -> dict[str, Any]:
    if not planner_raw:
        return {}
    if isinstance(planner_raw, dict):
        return planner_raw
    try:
        return json.loads(planner_raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def _build_report_sections(summaries: list[dict[str, Any]]) -> list[ReportSection]:
    sections: list[ReportSection] = []
    for s in summaries:
        sub = s.get("subtopic", "General")
        kf = s.get("key_findings", [])
        ev = s.get("supporting_evidence", [])
        stats = s.get("important_statistics", [])
        raw_contra = s.get("contradictions", [])
        raw_cites = s.get("citations", [])

        contradictions = [
            ReportContradiction(
                topic=c.get("topic", "Conflict"),
                statements=c.get("statements", []),
                subtopic=sub,
                severity=c.get("severity", "medium"),
            )
            for c in raw_contra if isinstance(c, dict)
        ]

        citations = [
            ReportCitation(
                claim=c.get("claim", ""),
                source=c.get("source", ""),
                supporting_chunk_ids=c.get("supporting_chunk_ids", []),
                subtopic=sub,
            )
            for c in raw_cites if isinstance(c, dict)
        ]

        sections.append(ReportSection(
            title=sub,
            summary=s.get("executive_summary", f"Analysis of {sub}."),
            key_findings=kf if isinstance(kf, list) else [],
            evidence_highlights=ev if isinstance(ev, list) else [],
            statistics=stats if isinstance(stats, list) else [],
            contradictions=contradictions,
            citations=citations,
            confidence_score=s.get("confidence_score", 0) or s.get("summary_score", 0),
            citation_count=s.get("citation_count", 0),
            source_count=s.get("source_count", 0),
        ))

    return sections


def _aggregate_key_findings(summaries: list[dict[str, Any]]) -> list[str]:
    findings: list[str] = []
    seen: set[str] = set()
    for s in summaries:
        for f in s.get("key_findings", []):
            if isinstance(f, str) and f not in seen:
                seen.add(f)
                findings.append(f)
    return findings


def _build_introduction(query: str, research_goal: str, planner: dict[str, Any] | None) -> str:
    parts = [f"This report presents a comprehensive investigation into: {query}."]
    if research_goal:
        parts.append(f"\n\nThe primary research goal is: {research_goal}")
    if planner:
        subs = planner.get("subtopics", [])
        if subs:
            parts.append(f"\n\nThe analysis covers {len(subs)} key subtopics: "
                         f"{'; '.join(subs[:5])}.")
        keywords = planner.get("keywords", [])
        if keywords:
            parts.append(f"\n\nCore research keywords: {', '.join(keywords[:8])}.")
    parts.append("\n\nThis report synthesises findings from multiple sources, "
                 "evaluates evidence quality, identifies research gaps, "
                 "and provides actionable recommendations.")
    return "".join(parts)


def _build_methodology(planner: dict[str, Any] | None) -> str:
    method = planner.get("methodology", "literature review") if planner else "literature review"
    parts = [
        f"This research was conducted using a {method} approach.",
        "\n\nThe methodology consisted of:",
        "\n1. **Planning**: Definition of research questions, subtopics, and search strategy.",
        "\n2. **Retrieval**: Multi-source evidence collection with relevance ranking and deduplication.",
        "\n3. **Analysis**: Evidence synthesis, citation tracking, and contradiction detection.",
        "\n4. **Gap Analysis**: Identification of missing knowledge, weak evidence, and unresolved conflicts.",
        "\n5. **Synthesis**: Integration of findings into a structured research report.",
    ]
    if planner:
        queries = planner.get("search_queries", [])
        if queries:
            parts.append(f"\n\nSearch strategy included {len(queries)} targeted queries "
                         f"across multiple collections.")
    parts.append("\n\nConfidence scores reflect the strength of supporting evidence, "
                 "citation volume, source diversity, and consistency of findings.")
    return "".join(parts)


def _build_executive_summary(
    query: str,
    sections: list[ReportSection],
    gaps: list[dict[str, Any]],
    key_findings: list[str],
) -> str:
    n_sections = len(sections)
    n_gaps = len(gaps)
    n_findings = len(key_findings)

    if n_findings == 0 and n_sections == 0:
        return f"Insufficient data to generate an executive summary for '{query}'."

    avg_conf = round(sum(s.confidence_score for s in sections) / max(n_sections, 1), 1) if sections else 0

    parts = [
        f"This report investigates '{query}' across {n_sections} subtopics "
        f"with an average confidence score of {avg_conf:.1f}/100."
    ]

    if n_findings > 0:
        parts.append(f"\n\nThe analysis yielded {n_findings} key findings.")

    if sections:
        highest = max(sections, key=lambda s: s.confidence_score)
        parts.append(f"\n\nThe strongest evidence is in '{highest.title}' "
                     f"(confidence: {highest.confidence_score:.1f}/100).")

    if n_gaps > 0:
        critical = sum(1 for g in gaps if g.get("severity", "") == "critical")
        high = sum(1 for g in gaps if g.get("severity", "") == "high")
        if critical or high:
            parts.append(f"\n\nThe analysis identified {n_gaps} research gaps "
                         f"({critical} critical, {high} high severity) "
                         f"that limit the strength of conclusions.")
        else:
            parts.append(f"\n\nThe analysis identified {n_gaps} research gaps.")

    return "".join(parts)


def _build_conclusion(query: str, sections: list[ReportSection], gaps: list[dict[str, Any]]) -> str:
    n_sections = len(sections)
    n_gaps = len(gaps)
    covered_subs = [s.title for s in sections]

    parts = [
        f"This research has examined '{query}' through {n_sections} subtopics."
    ]

    if covered_subs:
        parts.append(f"\n\nThe analysis covered: {'; '.join(covered_subs[:6])}.")

    if n_gaps == 0:
        parts.append("\n\nNo significant research gaps were identified, "
                     "indicating good coverage of the topic.")
    else:
        parts.append(f"\n\nThe identification of {n_gaps} research gaps suggests "
                     "that further investigation is warranted in specific areas.")

    total_cites = sum(s.citation_count for s in sections)
    if total_cites > 0:
        parts.append(f"\n\nFindings are supported by {total_cites} citations across "
                     f"{len(covered_subs)} subtopics.")

    parts.append("\n\nThe methodology employed provides a structured and reproducible "
                 "approach to evidence synthesis. Results should be interpreted "
                 "considering the limitations and gaps documented in this report.")

    return "".join(parts)


def _extract_limitations(gaps: list[dict[str, Any]]) -> list[str]:
    limitations: list[str] = []
    seen: set[str] = set()

    for g in gaps:
        gap_type = g.get("gap_type", "")
        desc = g.get("description", "")

        if gap_type == "LOW_EVIDENCE":
            text = f"Limited evidence: {desc[:150]}"
        elif gap_type == "LOW_CITATION_COVERAGE":
            text = f"Citation gap: {desc[:150]}"
        elif gap_type == "INSUFFICIENT_SOURCE_DIVERSITY":
            text = f"Source diversity limitation: {desc[:150]}"
        elif gap_type == "LOW_CONFIDENCE_SUMMARY":
            text = f"Low confidence finding: {desc[:150]}"
        elif gap_type == "OUTDATED_INFORMATION":
            text = f"Temporal limitation: {desc[:150]}"
        else:
            continue

        if text not in seen:
            seen.add(text)
            limitations.append(text)

    if not limitations:
        limitations.append("No significant limitations identified beyond those documented in research gaps.")

    return limitations[:8]


def _extract_recommendations(gaps: list[dict[str, Any]]) -> list[str]:
    recommendations: list[str] = []
    seen: set[str] = set()

    for g in gaps:
        remediation = g.get("remediation", {})
        if isinstance(remediation, dict):
            for action in remediation.get("recommended_actions", []):
                if action not in seen:
                    seen.add(action)
                    recommendations.append(action)

    if not recommendations:
        recommendations.append("Conduct further research to strengthen evidence base.")
        recommendations.append("Expand source diversity to improve coverage.")
        recommendations.append("Validate findings through expert review.")

    return recommendations[:10]


def _extract_future_research(gaps: list[dict[str, Any]]) -> list[str]:
    future: list[str] = []
    seen: set[str] = set()

    for g in gaps:
        gap_type = g.get("gap_type", "")
        desc = g.get("description", "")
        remediation = g.get("remediation", {})

        if gap_type == "MISSING_SUBTOPIC":
            sub = g.get("affected_subtopics", [])
            if sub:
                text = f"Investigate uncovered subtopic: {sub[0]}"
                if text not in seen:
                    seen.add(text)
                    future.append(text)
        elif gap_type == "MISSING_RESEARCH_QUESTION":
            text = f"Address unanswered research question: {desc[:150]}"
            if text not in seen:
                seen.add(text)
                future.append(text)
        elif gap_type == "CONTRADICTION":
            text = f"Resolve conflicting evidence: {desc[:150]}"
            if text not in seen:
                seen.add(text)
                future.append(text)
        elif gap_type == "MISSING_RISK_ANALYSIS":
            text = f"Perform risk analysis for: {desc[:150]}"
            if text not in seen:
                seen.add(text)
                future.append(text)

        if isinstance(remediation, dict):
            for q in remediation.get("recommended_queries", []):
                text = f"Explore: {q}"
                if text not in seen:
                    seen.add(text)
                    future.append(text)

    if not future:
        future.append("Expand the scope of literature search to cover identified gaps.")
        future.append("Consider complementary research methodologies.")

    return future[:12]
