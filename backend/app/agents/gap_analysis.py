from __future__ import annotations

import json
import re
from typing import Any

from app.schemas.gap_detection import GapType, ResearchGap
from app.agents.gap_severity import compute_severity
from app.agents.gap_remediation import generate_remediation


def detect_all_gaps(
    planner_raw: str | None,
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> list[ResearchGap]:
    """Run all gap detectors and return sorted list of ResearchGap."""
    planner = _parse_planner(planner_raw)

    gaps: list[ResearchGap] = []

    gaps.extend(_detect_missing_subtopics(planner, summaries, bundles))
    gaps.extend(_detect_low_evidence(planner, summaries, bundles))
    gaps.extend(_detect_low_citation_coverage(planner, summaries, bundles))
    gaps.extend(_detect_contradictions(planner, summaries, bundles))
    gaps.extend(_detect_outdated_information(planner, summaries, bundles))
    gaps.extend(_detect_missing_risk_analysis(planner, summaries, bundles))
    gaps.extend(_detect_missing_priority_area(planner, summaries, bundles))
    gaps.extend(_detect_missing_research_question(planner, summaries, bundles))
    gaps.extend(_detect_insufficient_source_diversity(planner, summaries, bundles))
    gaps.extend(_detect_low_confidence_summary(planner, summaries, bundles))

    gaps.sort(key=_sort_key, reverse=True)
    return gaps


def _parse_planner(planner_raw: str | None) -> dict[str, Any]:
    if not planner_raw:
        return {}
    if isinstance(planner_raw, dict):
        return planner_raw
    try:
        return json.loads(planner_raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def _sort_key(gap: ResearchGap) -> int:
    sev_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    sev = gap.severity.value if hasattr(gap.severity, "value") else str(gap.severity)
    return sev_order.get(sev, 0)


# ── Detector implementations ────────────────────────────


def _detect_missing_subtopics(
    planner: dict[str, Any],
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> list[ResearchGap]:
    gaps: list[ResearchGap] = []
    planned = _list_clean(planner.get("subtopics", []))
    covered = _covered_set(summaries)
    missing = [s for s in planned if s.lower() not in covered]

    for sub in missing:
        sev = compute_severity(GapType.MISSING_SUBTOPIC, planner)
        gaps.append(ResearchGap(
            gap_id=f"missing_subtopic_{sub[:20].replace(' ', '_').lower()}",
            gap_type=GapType.MISSING_SUBTOPIC,
            description=f"Subtopics planned but not covered in any summary: '{sub}'",
            severity=sev,
            affected_subtopics=[sub],
            supporting_evidence=f"Planner included '{sub}' but no summary addresses it",
            remediation=generate_remediation(GapType.MISSING_SUBTOPIC, planner, summaries, bundles),
            confidence=85.0,
        ))
    return gaps


def _detect_low_evidence(
    planner: dict[str, Any],
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> list[ResearchGap]:
    gaps: list[ResearchGap] = []
    for s in summaries:
        sub = s.get("subtopic", "unknown")
        cites = s.get("citation_count", 0)
        conf = s.get("confidence_score", 50)
        if cites < 2 and conf < 50:
            sev = compute_severity(GapType.LOW_EVIDENCE, planner, s)
            gaps.append(ResearchGap(
                gap_id=f"low_evidence_{sub[:20].replace(' ', '_').lower()}",
                gap_type=GapType.LOW_EVIDENCE,
                description=f"Insufficient evidence for '{sub}': only {cites} citation(s) with confidence {conf}",
                severity=sev,
                affected_subtopics=[sub],
                supporting_evidence=f"Citation count={cites}, confidence={conf}",
                remediation=generate_remediation(GapType.LOW_EVIDENCE, planner, summaries, bundles),
                confidence=70.0,
            ))
    return gaps


def _detect_low_citation_coverage(
    planner: dict[str, Any],
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> list[ResearchGap]:
    gaps: list[ResearchGap] = []
    for s in summaries:
        sub = s.get("subtopic", "unknown")
        cites = s.get("citation_count", 0)
        srcs = s.get("source_count", 0)
        if cites == 0 and srcs == 0:
            sev = compute_severity(GapType.LOW_CITATION_COVERAGE, planner, s)
            gaps.append(ResearchGap(
                gap_id=f"low_citation_{sub[:20].replace(' ', '_').lower()}",
                gap_type=GapType.LOW_CITATION_COVERAGE,
                description=f"No citations for '{sub}': all claims are unsupported",
                severity=sev,
                affected_subtopics=[sub],
                supporting_evidence=f"citation_count={cites}, source_count={srcs}",
                remediation=generate_remediation(GapType.LOW_CITATION_COVERAGE, planner, summaries, bundles),
                confidence=80.0,
            ))
    return gaps


def _detect_contradictions(
    planner: dict[str, Any],
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> list[ResearchGap]:
    gaps: list[ResearchGap] = []
    for s in summaries:
        contra = s.get("contradictions", [])
        if not contra:
            continue
        sub = s.get("subtopic", "unknown")
        # Flatten into individual gap per contradiction
        for i, c in enumerate(contra):
            if isinstance(c, dict):
                topic = c.get("topic", f"contradiction_{i}")
                statements = c.get("statements", [])
                sev = compute_severity(GapType.CONTRADICTION, planner, s)
                gaps.append(ResearchGap(
                    gap_id=f"contradiction_{sub[:15]}_{i}".replace(" ", "_").lower(),
                    gap_type=GapType.CONTRADICTION,
                    description=f"Unresolved contradiction in '{sub}': {topic}",
                    severity=sev,
                    affected_subtopics=[sub],
                    supporting_evidence="; ".join(statements[:3]) if statements else "Contradictory statements detected",
                    remediation=generate_remediation(GapType.CONTRADICTION, planner, summaries, bundles),
                    confidence=75.0,
                ))
    if not gaps:
        # Still flag if no contradictions were found in any summary (may indicate shallow analysis)
        pass
    return gaps


def _detect_outdated_information(
    planner: dict[str, Any],
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> list[ResearchGap]:
    gaps: list[ResearchGap] = []
    current_year = 2026
    for s in summaries:
        text = _summary_text_flat(s)
        years_found = set(re.findall(r"\b(19\d{2}|20[0-2]\d)\b", text))
        recent = {y for y in years_found if int(y) >= current_year - 2}
        if years_found and not recent:
            sub = s.get("subtopic", "unknown")
            old_years = sorted(years_found, reverse=True)[:3]
            sev = compute_severity(GapType.OUTDATED_INFORMATION, planner, s)
            gaps.append(ResearchGap(
                gap_id=f"outdated_{sub[:20].replace(' ', '_').lower()}",
                gap_type=GapType.OUTDATED_INFORMATION,
                description=f"No recent sources in '{sub}': latest reference is from {old_years[0] if old_years else 'unknown'}",
                severity=sev,
                affected_subtopics=[sub],
                supporting_evidence=f"Years referenced: {', '.join(old_years)}",
                remediation=generate_remediation(GapType.OUTDATED_INFORMATION, planner, summaries, bundles),
                confidence=65.0,
            ))
    return gaps


def _detect_missing_risk_analysis(
    planner: dict[str, Any],
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> list[ResearchGap]:
    gaps: list[ResearchGap] = []
    risks = _list_clean(planner.get("risk_areas", []))
    if not risks:
        return gaps
    covered = _risk_covered_set(risks, summaries)
    for risk in risks:
        if risk.lower() not in covered:
            sev = compute_severity(GapType.MISSING_RISK_ANALYSIS, planner)
            gaps.append(ResearchGap(
                gap_id=f"missing_risk_{risk[:20].replace(' ', '_').lower()}",
                gap_type=GapType.MISSING_RISK_ANALYSIS,
                description=f"Risk area identified by planner but not analysed: '{risk}'",
                severity=sev,
                affected_subtopics=[risk],
                supporting_evidence=f"Planner flagged '{risk}' as a risk area but no summary discusses it",
                remediation=generate_remediation(GapType.MISSING_RISK_ANALYSIS, planner, summaries, bundles),
                confidence=85.0,
            ))
    return gaps


def _detect_missing_priority_area(
    planner: dict[str, Any],
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> list[ResearchGap]:
    gaps: list[ResearchGap] = []
    priorities = _list_clean(planner.get("priority_areas", []))
    if not priorities:
        return gaps
    covered = _priority_covered_set(priorities, summaries)
    for p in priorities:
        if p.lower() not in covered:
            sev = compute_severity(GapType.MISSING_PRIORITY_AREA, planner)
            gaps.append(ResearchGap(
                gap_id=f"missing_priority_{p[:20].replace(' ', '_').lower()}",
                gap_type=GapType.MISSING_PRIORITY_AREA,
                description=f"Priority area identified by planner but not covered: '{p}'",
                severity=sev,
                affected_subtopics=[p],
                supporting_evidence=f"Planner prioritised '{p}' but no summary addresses it",
                remediation=generate_remediation(GapType.MISSING_PRIORITY_AREA, planner, summaries, bundles),
                confidence=85.0,
            ))
    return gaps


def _detect_missing_research_question(
    planner: dict[str, Any],
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> list[ResearchGap]:
    gaps: list[ResearchGap] = []
    questions = _list_clean(planner.get("research_questions", []))
    if not questions:
        return gaps
    from app.agents.gap_coverage import build_question_mapping
    mapping = build_question_mapping(questions, summaries)
    for q, status in mapping.items():
        if status == "uncovered":
            sev = compute_severity(GapType.MISSING_RESEARCH_QUESTION, planner)
            gaps.append(ResearchGap(
                gap_id=f"unanswered_q_{hash(q) % 10000:04d}",
                gap_type=GapType.MISSING_RESEARCH_QUESTION,
                description=f"Research question not answered by any summary: '{q[:120]}'",
                severity=sev,
                affected_subtopics=[],
                supporting_evidence=f"Question: {q}",
                remediation=generate_remediation(GapType.MISSING_RESEARCH_QUESTION, planner, summaries, bundles),
                confidence=80.0,
            ))
    return gaps


def _detect_insufficient_source_diversity(
    planner: dict[str, Any],
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> list[ResearchGap]:
    gaps: list[ResearchGap] = []
    all_sources: set[str] = set()
    source_counts: dict[str, int] = {}
    for s in summaries:
        srcs = s.get("supporting_evidence", [])
        for ev in srcs:
            src_name = _guess_source(ev)
            all_sources.add(src_name)
            source_counts[src_name] = source_counts.get(src_name, 0) + 1

    if len(all_sources) <= 1 and len(summaries) > 1:
        dominant = list(all_sources)[0] if all_sources else "unknown"
        sev = compute_severity(GapType.INSUFFICIENT_SOURCE_DIVERSITY, planner)
        gaps.append(ResearchGap(
            gap_id="low_source_diversity",
            gap_type=GapType.INSUFFICIENT_SOURCE_DIVERSITY,
            description=f"Single-source dominance: '{dominant}' is the only source type across all summaries",
            severity=sev,
            affected_subtopics=[s.get("subtopic", "") for s in summaries],
            supporting_evidence=f"Unique sources: {len(all_sources)} across {len(summaries)} summaries",
            remediation=generate_remediation(GapType.INSUFFICIENT_SOURCE_DIVERSITY, planner, summaries, bundles),
            confidence=70.0,
        ))
    return gaps


def _detect_low_confidence_summary(
    planner: dict[str, Any],
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> list[ResearchGap]:
    gaps: list[ResearchGap] = []
    for s in summaries:
        conf = s.get("confidence_score", 50) or s.get("summary_score", 50)
        sub = s.get("subtopic", "unknown")
        if conf < 30:
            sev = compute_severity(GapType.LOW_CONFIDENCE_SUMMARY, planner, s)
            gaps.append(ResearchGap(
                gap_id=f"low_confidence_{sub[:20].replace(' ', '_').lower()}",
                gap_type=GapType.LOW_CONFIDENCE_SUMMARY,
                description=f"Summary for '{sub}' has low confidence: score={conf}",
                severity=sev,
                affected_subtopics=[sub],
                supporting_evidence=f"confidence_score={conf}, citation_count={s.get('citation_count', 0)}",
                remediation=generate_remediation(GapType.LOW_CONFIDENCE_SUMMARY, planner, summaries, bundles),
                confidence=conf,
            ))
    return gaps


# ── Internal helpers ────────────────────────────────────


def _list_clean(items: list[Any]) -> list[str]:
    return [str(i).strip() for i in items if i and str(i).strip()]


def _covered_set(summaries: list[dict[str, Any]]) -> set[str]:
    covered: set[str] = set()
    for s in summaries:
        sub = s.get("subtopic", "")
        if sub:
            covered.add(sub.lower().strip())
        for f in s.get("key_findings", []):
            if isinstance(f, str):
                covered.add(f.lower().strip()[:40])
    return covered


def _risk_covered_set(risks: list[str], summaries: list[dict[str, Any]]) -> set[str]:
    covered: set[str] = set()
    for s in summaries:
        text = _summary_text_flat(s).lower()
        for r in risks:
            tokens = set(re.findall(r"\b[a-zA-Z]{4,}\b", r.lower()))
            if tokens and sum(1 for t in tokens if t in text) >= max(1, len(tokens) // 3):
                covered.add(r.lower())
    return covered


def _priority_covered_set(priorities: list[str], summaries: list[dict[str, Any]]) -> set[str]:
    covered: set[str] = set()
    for s in summaries:
        text = _summary_text_flat(s).lower()
        for p in priorities:
            tokens = set(re.findall(r"\b[a-zA-Z]{4,}\b", p.lower()))
            if tokens and sum(1 for t in tokens if t in text) >= max(1, len(tokens) // 3):
                covered.add(p.lower())
    return covered


def _summary_text_flat(s: dict[str, Any]) -> str:
    parts = [
        s.get("executive_summary", ""),
        " ".join(s.get("key_findings", [])),
        " ".join(s.get("supporting_evidence", [])),
        " ".join(s.get("consensus_points", [])),
        " ".join(s.get("important_statistics", [])),
    ]
    return " ".join(p for p in parts if p)


def _guess_source(evidence_text: str) -> str:
    """Heuristic to identify source type from evidence text."""
    text_lower = evidence_text.lower()
    if any(x in text_lower for x in ["doi:", "doi.org", "arxiv"]):
        return "arxiv"
    if any(x in text_lower for x in ["ieee", "acm"]):
        return "conference"
    if any(x in text_lower for x in ["springer", "elsevier", "nature"]):
        return "journal"
    if any(x in text_lower for x in ["report", "whitepaper", "white paper"]):
        return "industry"
    return "general"
