from __future__ import annotations

from typing import Any

from app.schemas.gap_detection import GapType, RemediationSuggestion


def generate_remediation(
    gap_type: GapType,
    planner: dict[str, Any] | None,
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> RemediationSuggestion:
    """Generate remediation suggestions tailored to the gap type and available context."""
    generator = _REMEDIATORS.get(gap_type, _default_remediation)
    return generator(planner, summaries, bundles)


def _missing_subtopic_remediation(
    planner: dict[str, Any] | None,
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> RemediationSuggestion:
    queries = planner.get("search_queries", [])[:3] if planner else []
    covered = {s.get("subtopic", "").lower() for s in summaries}
    if planner:
        for sub in planner.get("subtopics", []):
            if sub.lower() not in covered:
                queries.append(f"latest research on {sub}")
                queries.append(f"{sub} 2025 2026 survey")
    return RemediationSuggestion(
        recommended_queries=queries[:5],
        recommended_sources=["arxiv", "google scholar", "springer"],
        recommended_actions=[
            "Run targeted search queries for uncovered subtopics",
            "Expand collection scope beyond current sources",
        ],
    )


def _low_evidence_remediation(
    planner: dict[str, Any] | None,
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> RemediationSuggestion:
    queries: list[str] = []
    for s in summaries:
        if s.get("citation_count", 0) < 3:
            sub = s.get("subtopic", "")
            if sub:
                queries.append(f"additional evidence for {sub}")
    return RemediationSuggestion(
        recommended_queries=queries[:5] or ["broader search terms for low-evidence topics"],
        recommended_sources=["google scholar", "semantic scholar", "pubmed"],
        recommended_actions=[
            "Broaden search queries for low-evidence topics",
            "Include grey literature and pre-prints",
            "Increase chunk overlap in ingestion pipeline",
        ],
    )


def _low_citation_remediation(
    planner: dict[str, Any] | None,
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> RemediationSuggestion:
    return RemediationSuggestion(
        recommended_queries=["retrieve additional supporting sources"],
        recommended_sources=["crossref", "scopus", "web of science"],
        recommended_actions=[
            "Increase top-K retrieval for each subtopic",
            "Add citation-chaining retrieval strategy",
        ],
    )


def _contradiction_remediation(
    planner: dict[str, Any] | None,
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> RemediationSuggestion:
    topics: set[str] = set()
    for s in summaries:
        for c in s.get("contradictions", []):
            if isinstance(c, dict):
                topics.add(c.get("topic", ""))
    queries = [f"resolve conflicting findings about {t}" for t in topics if t]
    return RemediationSuggestion(
        recommended_queries=queries[:5],
        recommended_sources=["meta-analyses", "systematic reviews", "expert interviews"],
        recommended_actions=[
            "Consult meta-analyses to resolve contradictions",
            "Flag contradictions for human expert review",
            "Consider temporal ordering of conflicting claims",
        ],
    )


def _outdated_remediation(
    planner: dict[str, Any] | None,
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> RemediationSuggestion:
    return RemediationSuggestion(
        recommended_queries=["2025 2026 latest developments", "recent advances survey"],
        recommended_sources=["techcrunch", "nature", "science direct"],
        recommended_actions=[
            "Date-filtered search for recent publications",
            "Monitor pre-print servers for latest findings",
        ],
    )


def _missing_risk_remediation(
    planner: dict[str, Any] | None,
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> RemediationSuggestion:
    risks = planner.get("risk_areas", []) if planner else []
    queries = [f"risk analysis of {r}" for r in risks[:3]]
    return RemediationSuggestion(
        recommended_queries=queries or ["comprehensive risk assessment"],
        recommended_sources=["ieee", "acm", "security conferences"],
        recommended_actions=[
            "Perform structured risk analysis for each risk area",
            "Consult domain-specific safety and security literature",
        ],
    )


def _missing_priority_remediation(
    planner: dict[str, Any] | None,
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> RemediationSuggestion:
    priorities = planner.get("priority_areas", []) if planner else []
    queries = [f"priority research in {p}" for p in priorities[:3]]
    return RemediationSuggestion(
        recommended_queries=queries or ["priority area deep-dive"],
        recommended_sources=["google scholar", "research gate"],
        recommended_actions=[
            "Re-run retrieval with priority-focused queries",
            "Assign higher relevance weight to priority-area sources",
        ],
    )


def _missing_question_remediation(
    planner: dict[str, Any] | None,
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> RemediationSuggestion:
    questions = planner.get("research_questions", []) if planner else []
    queries = [f"research: {q}" for q in questions[:3]]
    return RemediationSuggestion(
        recommended_queries=queries,
        recommended_sources=["google scholar", "arxiv", "semantic scholar"],
        recommended_actions=[
            "Target each unanswered research question with dedicated queries",
            "Consider reformulating questions for better retrieval match",
        ],
    )


def _source_diversity_remediation(
    planner: dict[str, Any] | None,
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> RemediationSuggestion:
    return RemediationSuggestion(
        recommended_queries=["diverse perspectives", "alternative viewpoints"],
        recommended_sources=[
            "industry reports", "government publications", "conference proceedings",
            "dissertations", "patent filings",
        ],
        recommended_actions=[
            "Expand collection strategy to include non-academic sources",
            "Balance source types across academic, industry, and government",
            "Configure ingestion pipeline with additional source connectors",
        ],
    )


def _low_confidence_remediation(
    planner: dict[str, Any] | None,
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> RemediationSuggestion:
    return RemediationSuggestion(
        recommended_queries=["high-quality authoritative sources", "peer-reviewed surveys"],
        recommended_sources=["peer-reviewed journals", "authoritative textbooks"],
        recommended_actions=[
            "Prioritize authoritative and peer-reviewed sources",
            "Increase evidence threshold for low-confidence summaries",
            "Request human verification for critical claims",
        ],
    )


def _default_remediation(
    planner: dict[str, Any] | None,
    summaries: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> RemediationSuggestion:
    return RemediationSuggestion(
        recommended_queries=["further investigation required"],
        recommended_sources=["google scholar"],
        recommended_actions=["Review and expand research scope"],
    )


_REMEDIATORS = {
    GapType.MISSING_SUBTOPIC: _missing_subtopic_remediation,
    GapType.LOW_EVIDENCE: _low_evidence_remediation,
    GapType.LOW_CITATION_COVERAGE: _low_citation_remediation,
    GapType.CONTRADICTION: _contradiction_remediation,
    GapType.OUTDATED_INFORMATION: _outdated_remediation,
    GapType.MISSING_RISK_ANALYSIS: _missing_risk_remediation,
    GapType.MISSING_PRIORITY_AREA: _missing_priority_remediation,
    GapType.MISSING_RESEARCH_QUESTION: _missing_question_remediation,
    GapType.INSUFFICIENT_SOURCE_DIVERSITY: _source_diversity_remediation,
    GapType.LOW_CONFIDENCE_SUMMARY: _low_confidence_remediation,
}
