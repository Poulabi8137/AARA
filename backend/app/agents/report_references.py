from __future__ import annotations

from collections import Counter
from typing import Any

from app.schemas.report_generator import ReportReference, ReportCitation


def aggregate_references(summaries: list[dict[str, Any]]) -> list[ReportReference]:
    """Collect, deduplicate, and order all citations and sources from summaries."""
    ref_map: dict[str, dict[str, Any]] = {}
    id_counter = 0

    for s in summaries:
        subtopic = s.get("subtopic", "unknown")
        citations = s.get("citations", [])

        if not isinstance(citations, list):
            continue

        for c in citations:
            if not isinstance(c, dict):
                continue
            source = c.get("source", "unknown") or "unknown"
            claim = c.get("claim", "")
            chunk_ids = c.get("supporting_chunk_ids", [])

            key = _reference_key(source, claim)
            if key not in ref_map:
                id_counter += 1
                ref_map[key] = {
                    "reference_id": f"R{id_counter:03d}",
                    "source": source,
                    "claims": [],
                    "subtopics": set(),
                    "occurrence_count": 0,
                }

            entry = ref_map[key]
            if claim and claim not in entry["claims"]:
                entry["claims"].append(claim[:200])
            entry["subtopics"].add(subtopic)
            entry["occurrence_count"] += 1

    # Sort by occurrence count (most cited first)
    sorted_entries = sorted(ref_map.values(), key=lambda e: -e["occurrence_count"])

    return [
        ReportReference(
            reference_id=e["reference_id"],
            source=e["source"],
            claims=e["claims"],
            subtopics=sorted(e["subtopics"]),
            occurrence_count=e["occurrence_count"],
        )
        for e in sorted_entries
    ]


def build_citation_list(summaries: list[dict[str, Any]]) -> list[ReportCitation]:
    """Build a flat list of all citations from all summaries."""
    citations: list[ReportCitation] = []
    seen: set[str] = set()

    for s in summaries:
        subtopic = s.get("subtopic", "unknown")
        raw = s.get("citations", [])

        if not isinstance(raw, list):
            continue

        for c in raw:
            if not isinstance(c, dict):
                continue
            source = c.get("source", "")
            claim = c.get("claim", "")
            chunk_ids = c.get("supporting_chunk_ids", [])

            dedup_key = f"{source}|{claim}" if claim else f"{source}|{chunk_ids}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            citations.append(ReportCitation(
                claim=claim[:200],
                source=source,
                supporting_chunk_ids=chunk_ids[:5],
                subtopic=subtopic,
            ))

    return citations


def build_contradiction_list(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collect all contradictions from all summaries."""
    from app.schemas.report_generator import ReportContradiction

    result: list[ReportContradiction] = []
    for s in summaries:
        subtopic = s.get("subtopic", "unknown")
        raw = s.get("contradictions", [])

        if not isinstance(raw, list):
            continue

        for c in raw:
            if not isinstance(c, dict):
                continue
            result.append(ReportContradiction(
                topic=c.get("topic", f"Contradiction in {subtopic}"),
                statements=c.get("statements", []),
                subtopic=subtopic,
                severity=c.get("severity", "medium"),
            ))

    return result


def _reference_key(source: str, claim: str) -> str:
    """Generate a deduplication key for a citation."""
    s = source.strip().lower() if source else "unknown"
    c = claim.strip().lower()[:100] if claim else ""
    return f"{s}|{c}"
