from __future__ import annotations

import re

from app.core.logging import get_logger
from app.summarization.config import get_summarization_settings
from app.summarization.models import (
    EvidenceGroup,
    SummaryLevel,
    SummaryResult,
    ValidationReport,
)

logger = get_logger("summarization.validator")
settings = get_summarization_settings()

_LEVEL_TOKEN_RANGES: dict[str, tuple[int, int]] = {
    "brief": (100, 500),
    "standard": (300, 1200),
    "detailed": (800, 3000),
    "literature_review": (1000, 4000),
    "executive_summary": (200, 800),
}

_REQUIRED_SECTIONS: dict[str, list[str]] = {
    "brief": ["abstract", "conclusion"],
    "standard": [
        "abstract",
        "background",
        "methodology",
        "results",
        "discussion",
        "conclusion",
    ],
    "detailed": [
        "abstract",
        "background",
        "problem_statement",
        "methodology",
        "experimental_setup",
        "results",
        "discussion",
        "limitations",
        "future_work",
        "conclusion",
    ],
    "literature_review": [
        "abstract",
        "background",
        "methodology",
        "results",
        "discussion",
        "limitations",
        "future_work",
        "conclusion",
    ],
    "executive_summary": ["abstract", "conclusion"],
}


class SummaryValidator:
    def validate(
        self,
        result: SummaryResult,
        groups: list[EvidenceGroup],
    ) -> ValidationReport:
        report = ValidationReport()
        total_sources = sum(len(g.evidence) for g in groups)

        self._check_citation_completeness(result, total_sources, report)
        self._check_evidence_coverage(result, groups, report)
        self._check_duplicated_statements(result, report)
        self._check_unsupported_claims(result, report)
        self._check_confidence_thresholds(result, report)
        self._check_missing_sections(result, report)

        report.is_valid = len(report.errors) == 0

        logger.info(
            "summary validation complete",
            extra={
                "valid": report.is_valid,
                "errors": len(report.errors),
                "warnings": len(report.warnings),
            },
        )
        return report

    def _check_citation_completeness(
        self,
        result: SummaryResult,
        total_sources: int,
        report: ValidationReport,
    ) -> None:
        if not result.summary:
            report.errors.append("Summary is empty")
            return

        citations = re.findall(r"\[\d+\]", result.summary)
        if not citations and total_sources > 0:
            report.errors.append("No citations found in summary")

    def _check_evidence_coverage(
        self,
        result: SummaryResult,
        groups: list[EvidenceGroup],
        report: ValidationReport,
    ) -> None:
        total_sources = sum(len(g.evidence) for g in groups)
        if total_sources == 0:
            report.errors.append("No evidence sources provided")
            return

        cited_keys = set(re.findall(r"\[\d+\]", result.summary))
        total_keys = sum(len(g.citation_keys) for g in groups)
        if total_keys > 0 and len(cited_keys) < total_keys * 0.3:
            report.warnings.append(
                f"Low citation coverage: {len(cited_keys)}/{total_keys} citation keys used"
            )

    def _check_duplicated_statements(
        self,
        result: SummaryResult,
        report: ValidationReport,
    ) -> None:
        paragraphs = [p for p in result.summary.split("\n\n") if p.strip()]
        seen: set[str] = set()
        for para in paragraphs:
            key = para.strip()[:100].lower()
            if key in seen:
                report.warnings.append("Potentially duplicated statement found")
                break
            seen.add(key)

    def _check_unsupported_claims(
        self,
        result: SummaryResult,
        report: ValidationReport,
    ) -> None:
        sentences = re.split(r"[.!?\n]", result.summary)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            has_citation = bool(re.search(r"\[\d+\]", sentence))
            is_heading = sentence.startswith("#") or sentence.startswith("##")
            is_structural = any(
                kw in sentence.lower()
                for kw in [
                    "introduction",
                    "background",
                    "methodology",
                    "results",
                    "discussion",
                    "conclusion",
                    "references",
                ]
            )
            if (
                not has_citation
                and not is_heading
                and not is_structural
                and len(sentence) > 100
            ):
                report.warnings.append(
                    f"Long statement without citation: {sentence[:80]}..."
                )

    def _check_confidence_thresholds(
        self,
        result: SummaryResult,
        report: ValidationReport,
    ) -> None:
        for finding in result.findings:
            if finding.confidence < settings.confidence_threshold:
                report.warnings.append(
                    f"Low confidence finding: {finding.finding[:60]}..."
                )

    def _check_missing_sections(
        self,
        result: SummaryResult,
        report: ValidationReport,
    ) -> None:
        level_key = (
            result.metadata.level.value
            if isinstance(result.metadata.level, SummaryLevel)
            else result.metadata.level
        )
        required = _REQUIRED_SECTIONS.get(level_key, [])
        if not result.sections:
            return
        found_sections = {s.type.value for s in result.sections}
        for section in required:
            if section not in found_sections:
                report.missing_sections.append(section)
        if report.missing_sections:
            report.errors.append(
                f"Missing sections: {', '.join(report.missing_sections)}"
            )
