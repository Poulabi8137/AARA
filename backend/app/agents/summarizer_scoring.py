from __future__ import annotations

from typing import Any

from app.schemas.summarizer import SectionSummary


def compute_summary_quality(summary: SectionSummary, bundle: dict[str, Any] | None = None) -> SectionSummary:
    """Compute all quality scores for a SectionSummary."""

    # Coverage score: what fraction of key fields are populated
    coverage = 0.0
    checks = 0
    if summary.executive_summary and len(summary.executive_summary) >= 50:
        coverage += 25.0
    checks += 1
    if len(summary.key_findings) >= 2:
        coverage += 20.0
    elif len(summary.key_findings) >= 1:
        coverage += 10.0
    checks += 1
    if summary.supporting_evidence:
        coverage += 15.0
    checks += 1
    if summary.citations:
        coverage += 15.0
    checks += 1
    if summary.consensus_points:
        coverage += 15.0
    checks += 1
    if summary.important_statistics:
        coverage += 10.0
    checks += 1
    summary.coverage_score = round(min(100.0, coverage), 2)

    # Evidence density: findings and evidence per bundle
    total_items = (
        len(summary.key_findings)
        + len(summary.supporting_evidence)
        + len(summary.important_statistics)
        + len(summary.consensus_points)
    )
    density = min(100.0, total_items * 8.0)
    summary.evidence_density = round(density, 2)

    # Citation strength: how well-cited the summary is
    evidence_count = len(bundle.get("evidence", [])) if bundle else 0
    if evidence_count > 0 and summary.citations:
        cited_chunks: set[str] = set()
        for c in summary.citations:
            cited_chunks.update(c.supporting_chunk_ids)
        c_strength = min(100.0, (len(cited_chunks) / evidence_count) * 100)
    else:
        c_strength = 0.0
    summary.citation_strength = round(c_strength, 2)

    # Consistency score: penalise contradictions
    if summary.contradictions:
        raw = max(0.0, 100.0 - (len(summary.contradictions) * 20.0))
    else:
        raw = 100.0
    summary.consistency_score = round(raw, 2)

    # Overall summary score: weighted average
    overall = (
        summary.coverage_score * 0.30
        + summary.evidence_density * 0.20
        + summary.citation_strength * 0.25
        + summary.consistency_score * 0.25
    )
    summary.summary_score = round(overall, 2)

    return summary
