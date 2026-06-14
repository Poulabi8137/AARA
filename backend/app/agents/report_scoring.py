from __future__ import annotations

from typing import Any

from app.schemas.report_generator import ReportMetrics


def compute_report_quality(
    sections: list[dict[str, Any]],
    references: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
) -> ReportMetrics:
    """Compute quality scores for the generated report."""
    n_sections = len(sections)
    n_refs = len(references)
    total_cites = sum(s.get("citation_count", 0) for s in sections)
    total_stats = sum(1 for s in sections if s.get("statistics", []))
    total_contras = sum(1 for s in sections if s.get("contradictions", []))
    avg_conf = _average_confidence(sections)

    # Report completeness: sections present, refs present, gaps present
    completeness = _compute_completeness(n_sections, n_refs, bool(gaps), avg_conf)

    # Evidence strength: citations per section + stats coverage
    evidence_strength = _compute_evidence_strength(n_sections, total_cites, total_stats, avg_conf)

    # Citation strength: reference count / citation count quality
    citation_strength = _compute_citation_strength(n_refs, total_cites, n_sections)

    # Coverage: how well sections cover the topic (based on confidence + citations)
    coverage = _compute_coverage(n_sections, avg_conf, total_cites)

    # Overall quality: weighted composite
    quality = round(
        completeness * 0.25 +
        evidence_strength * 0.25 +
        citation_strength * 0.15 +
        coverage * 0.35,
        2,
    )

    return ReportMetrics(
        report_completeness=round(completeness, 2),
        evidence_strength=round(evidence_strength, 2),
        citation_strength=round(citation_strength, 2),
        coverage_score=round(coverage, 2),
        research_quality_score=quality,
        section_count=n_sections,
        reference_count=n_refs,
        citation_count=total_cites,
    )


def _average_confidence(sections: list[dict[str, Any]]) -> float:
    if not sections:
        return 0.0
    scores = [s.get("confidence_score", 0) for s in sections if s.get("confidence_score", 0) > 0]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def _compute_completeness(n_sections: int, n_refs: int, has_gaps: bool, avg_conf: float) -> float:
    score = 0.0
    # Sections (40%)
    score += min(40.0, n_sections * 10.0)
    # References (25%)
    score += min(25.0, n_refs * 5.0)
    # Gaps discussion (15%)
    if has_gaps:
        score += 15.0
    # Avg confidence (20%)
    score += (avg_conf / 100.0) * 20.0
    return min(100.0, score)


def _compute_evidence_strength(n_sections: int, total_cites: int, stats_count: int, avg_conf: float) -> float:
    if n_sections == 0:
        return 0.0
    score = 0.0
    # Citations per section (50%)
    cites_per = total_cites / max(n_sections, 1)
    score += min(50.0, cites_per * 10.0)
    # Statistics coverage (30%)
    stats_ratio = stats_count / max(n_sections, 1)
    score += stats_ratio * 30.0
    # Confidence (20%)
    score += (avg_conf / 100.0) * 20.0
    return min(100.0, score)


def _compute_citation_strength(n_refs: int, total_cites: int, n_sections: int) -> float:
    if n_sections == 0:
        return 0.0
    score = 0.0
    # Unique references (60%)
    score += min(60.0, n_refs * 6.0)
    # Citations per section (40%)
    cites_per = total_cites / max(n_sections, 1)
    score += min(40.0, cites_per * 8.0)
    return min(100.0, score)


def _compute_coverage(n_sections: int, avg_conf: float, total_cites: int) -> float:
    if n_sections == 0:
        return 0.0
    score = 0.0
    # Section breadth (40%)
    score += min(40.0, n_sections * 10.0)
    # Confidence (30%)
    score += (avg_conf / 100.0) * 30.0
    # Citation volume (30%)
    score += min(30.0, total_cites * 3.0)
    return min(100.0, score)
