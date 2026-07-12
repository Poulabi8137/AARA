from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any


STOP_WORDS = {
    "what",
    "how",
    "why",
    "does",
    "the",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "will",
    "would",
    "could",
    "should",
    "this",
    "that",
    "these",
    "those",
    "with",
    "from",
    "about",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "between",
    "such",
    "each",
    "your",
    "their",
    "its",
}


def _extract_key_terms(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {w for w in words if len(w) >= 4 and w not in STOP_WORDS}


def compute_question_coverage(
    planner_questions: list[str],
    answered_questions: list[str],
    summaries: list[dict[str, Any]],
) -> float:
    if not planner_questions:
        return 0.0
    if not summaries:
        return 0.0
    combined_texts: list[str] = []
    for s in summaries:
        parts = [
            s.get("subtopic", ""),
            s.get("executive_summary", ""),
            " ".join(s.get("key_findings", [])),
        ]
        combined_texts.append(" ".join(parts))
    combined_corpus = " ".join(combined_texts)
    corpus_terms = _extract_key_terms(combined_corpus) if combined_corpus else set()
    matched = 0
    for q in planner_questions:
        terms = _extract_key_terms(q)
        if not terms:
            matched += 1
            continue
        if len(terms & corpus_terms) / len(terms) >= 0.4:
            matched += 1
    return (matched / len(planner_questions)) * 100.0


def compute_citation_density(
    citations: list[dict[str, Any]],
    sections: list[dict[str, Any]],
) -> float:
    num_sections = max(len(sections), 1)
    avg = len(citations) / num_sections
    return min(avg / 2.0, 1.0) * 100.0


def compute_source_diversity(
    sources: list[str],
    citations: list[dict[str, Any]],
) -> float:
    source_names: list[str] = []
    for c in citations:
        src = c.get("source", "")
        if src:
            source_names.append(src)
    source_names.extend(s for s in sources if s)
    if not source_names:
        return 0.0
    counts = Counter(source_names)
    total = sum(counts.values())
    unique_count = len(counts)
    unique_score = min(unique_count / 5.0, 1.0) * 33.0
    most_common_ratio = counts.most_common(1)[0][1] / total
    concentration_score = (1.0 - most_common_ratio) * 33.0
    n = len(counts)
    if n <= 1:
        evenness_score = 0.0
    else:
        entropy = -sum((c / total) * math.log(c / total) for c in counts.values())
        max_entropy = math.log(n)
        evenness_score = (entropy / max_entropy) * 34.0
    return min(unique_score + concentration_score + evenness_score, 100.0)


def compute_evidence_strength(
    evidence_chunks: list[dict[str, Any]],
    key_findings: list[str],
) -> float:
    num_findings = max(len(key_findings), 1)
    if not evidence_chunks:
        return 0.0
    ratio = len(evidence_chunks) / num_findings
    score = min(ratio / 3.0, 1.0) * 100.0
    avg_relevance = 0.0
    relevance_count = 0
    for ch in evidence_chunks:
        rs = ch.get("relevance_score")
        if rs is not None:
            avg_relevance += float(rs)
            relevance_count += 1
    if relevance_count > 0:
        avg_relevance /= relevance_count
        score = score * (0.6 + 0.4 * (avg_relevance / 100.0))
    return min(score, 100.0)


def compute_summary_quality(
    summaries: list[dict[str, Any]],
) -> float:
    if not summaries:
        return 0.0
    total = 0.0
    count = 0
    quality_fields = [
        "coverage_score",
        "citation_strength",
        "consistency_score",
        "summary_score",
        "evidence_density",
    ]
    for s in summaries:
        for field in quality_fields:
            val = s.get(field)
            if val is not None:
                total += float(val)
                count += 1
    if count == 0:
        return 0.0
    return total / count


def compute_gap_coverage(
    gaps: list[dict[str, Any]],
) -> float:
    penalties = {"critical": 15.0, "high": 8.0, "medium": 4.0, "low": 1.0}
    total_penalty = 0.0
    for g in gaps:
        severity = g.get("severity", "low")
        total_penalty += penalties.get(severity, 1.0)
    return max(100.0 - total_penalty, 0.0)


def compute_report_completeness(
    report: dict[str, Any] | None,
    sections: list[dict[str, Any]],
) -> float:
    if report is None:
        return 0.0
    expected = {
        "executive_summary",
        "introduction",
        "methodology",
        "conclusion",
        "key_findings",
        "limitations",
        "recommendations",
        "future_research",
    }
    present = sum(
        1 for key in expected if report.get(key) is not None and report.get(key) != ""
    )
    return (present / len(expected)) * 100.0


def _detect_hallucination_patterns(text: str) -> list[str]:
    """Detect linguistic patterns that correlate with hallucinated content."""
    patterns = []
    hedging_patterns = [
        r"\bmay\b",
        r"\bmight\b",
        r"\bcould\b",
        r"\bpossibly\b",
        r"\bpresumably\b",
        r"\bto the best of our knowledge\b",
        r"\bit is believed\b",
        r"\bsome argue\b",
        r"\bit is thought\b",
    ]
    unsupported_absolute = [
        r"\balways\b",
        r"\bnever\b",
        r"\bevery\b",
        r"\bno one\b",
        r"\beveryone\b",
        r"\bdefinitely\b",
        r"\bundoubtedly\b",
        r"\bproves\b",
        r"\birrefutably\b",
    ]
    for pat in hedging_patterns:
        if re.search(pat, text, re.IGNORECASE):
            patterns.append(f"hedging: {pat}")
            break
    for pat in unsupported_absolute:
        if re.search(pat, text, re.IGNORECASE):
            patterns.append(f"unsupported absolute: {pat}")
            break
    speculative_phrases = [
        "it would seem",
        "one can imagine",
        "it is conceivable",
        "it stands to reason",
        "it goes without saying",
        "as one might expect",
        "naturally",
    ]
    for phrase in speculative_phrases:
        if phrase in text.lower():
            patterns.append(f"speculative: {phrase}")
            break
    return patterns


def compute_hallucination_proxy(
    report: dict[str, Any] | None,
    sections: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    key_findings: list[str],
) -> float:
    if report is None or not sections:
        return 100.0
    cited_chunk_ids: set[str] = set()
    supported_claims: set[str] = set()
    for c in citations:
        cids = c.get("supporting_chunk_ids", [])
        cited_chunk_ids.update(cids)
        claim = c.get("claim", "")
        if claim:
            supported_claims.add(claim.lower().strip())
    total_claims = 0
    unsupported_claims = 0
    hallucination_patterns_found = 0

    def _has_support(findings: list[str]) -> list[bool]:
        results: list[bool] = []
        for finding in findings:
            finding_lower = finding.lower().strip()
            if not finding_lower:
                continue
            supported = False
            for claim_text in supported_claims:
                finding_terms = _extract_key_terms(finding_lower)
                claim_terms = _extract_key_terms(claim_text)
                if finding_terms and claim_terms:
                    overlap = finding_terms & claim_terms
                    if len(overlap) / len(finding_terms) >= 0.3:
                        supported = True
                        break
            results.append(supported)
        return results

    for sec in sections:
        for f_name in ["key_findings", "evidence_highlights"]:
            items = sec.get(f_name, [])
            if isinstance(items, list):
                results = _has_support(items)
                for supported in results:
                    total_claims += 1
                    if not supported:
                        unsupported_claims += 1
                    else:
                        txt = (
                            items[len(results) - 1]
                            if len(results) <= len(items)
                            else ""
                        )
                        if txt and _detect_hallucination_patterns(txt):
                            hallucination_patterns_found += 1

    conclusion = report.get("conclusion", "")
    if isinstance(conclusion, str) and conclusion.strip():
        total_claims += 1
        conclusion_terms = _extract_key_terms(conclusion)
        supported = False
        for claim_text in supported_claims:
            claim_terms = _extract_key_terms(claim_text)
            if conclusion_terms and claim_terms:
                overlap = conclusion_terms & claim_terms
                if len(overlap) / len(conclusion_terms) >= 0.3:
                    supported = True
                    break
        if not supported:
            unsupported_claims += 1
        hp = _detect_hallucination_patterns(conclusion)
        hallucination_patterns_found += len(hp)

    exec_summary = report.get("executive_summary", "")
    if isinstance(exec_summary, str) and exec_summary.strip():
        hp = _detect_hallucination_patterns(exec_summary)
        hallucination_patterns_found += len(hp)

    introduction = report.get("introduction", "")
    if isinstance(introduction, str) and introduction.strip():
        hp = _detect_hallucination_patterns(introduction)
        hallucination_patterns_found += len(hp)

    pattern_penalty = min(hallucination_patterns_found * 5.0, 30.0)
    base_risk = (unsupported_claims / max(total_claims, 1)) * 100.0
    return min(base_risk + pattern_penalty, 100.0)


def compute_research_quality(
    question_coverage: float,
    citation_density: float,
    source_diversity: float,
    evidence_strength: float,
    summary_quality: float,
    gap_coverage: float,
    report_completeness: float,
    hallucination_risk: float,
) -> float:
    weights = {
        "question_coverage": 0.20,
        "summary_quality": 0.15,
        "evidence_strength": 0.15,
        "report_completeness": 0.12,
        "citation_density": 0.10,
        "source_diversity": 0.10,
        "gap_coverage": 0.10,
        "hallucination_risk": 0.08,
    }
    score = (
        question_coverage * weights["question_coverage"]
        + summary_quality * weights["summary_quality"]
        + evidence_strength * weights["evidence_strength"]
        + report_completeness * weights["report_completeness"]
        + citation_density * weights["citation_density"]
        + source_diversity * weights["source_diversity"]
        + gap_coverage * weights["gap_coverage"]
        + (100.0 - hallucination_risk) * weights["hallucination_risk"]
    )
    return min(score, 100.0)


METRIC_REGISTRY = {
    "question_coverage": compute_question_coverage,
    "citation_density": compute_citation_density,
    "source_diversity": compute_source_diversity,
    "evidence_strength": compute_evidence_strength,
    "summary_quality": compute_summary_quality,
    "gap_coverage": compute_gap_coverage,
    "report_completeness": compute_report_completeness,
    "hallucination_risk": compute_hallucination_proxy,
    "research_quality": compute_research_quality,
}

METRIC_WEIGHTS = {
    "question_coverage": 0.20,
    "summary_quality": 0.15,
    "evidence_strength": 0.15,
    "report_completeness": 0.12,
    "citation_density": 0.10,
    "source_diversity": 0.10,
    "gap_coverage": 0.10,
    "hallucination_risk": 0.08,
}
