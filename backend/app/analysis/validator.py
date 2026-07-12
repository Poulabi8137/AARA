from __future__ import annotations

import re

from app.core.logging import get_logger
from app.analysis.config import get_analysis_settings
from app.analysis.models import (
    AnalysisResult,
    AnalysisValidationReport,
)
from app.summarization.models import EvidenceGroup

logger = get_logger("analysis.validator")
settings = get_analysis_settings()


class AnalysisValidator:
    def validate(
        self,
        result: AnalysisResult,
        groups: list[EvidenceGroup],
    ) -> AnalysisValidationReport:
        report = AnalysisValidationReport()

        self._check_unsupported_conclusions(result, report)
        self._check_weak_evidence(result, groups, report)
        self._check_duplicate_insights(result, report)
        self._check_contradictory_recommendations(result, report)
        self._check_citation_completeness(result, report)

        report.is_valid = len(report.errors) == 0

        logger.info(
            "analysis validation complete",
            extra={
                "valid": report.is_valid,
                "errors": len(report.errors),
                "warnings": len(report.warnings),
            },
        )
        return report

    def _check_unsupported_conclusions(
        self,
        result: AnalysisResult,
        report: AnalysisValidationReport,
    ) -> None:
        for consensus in result.consensus:
            if consensus.confidence < settings.consensus_threshold:
                report.unsupported_conclusions.append(
                    f"Low confidence consensus: {consensus.statement[:60]}..."
                )
                report.warnings.append(
                    f"Consensus below threshold: {consensus.statement[:60]}..."
                )

    def _check_weak_evidence(
        self,
        result: AnalysisResult,
        groups: list[EvidenceGroup],
        report: AnalysisValidationReport,
    ) -> None:
        for group in groups:
            for ev in group.evidence:
                if ev.score < settings.consensus_threshold:
                    report.weak_evidence.append(
                        f"Low score evidence ({ev.score:.2f}): {ev.source_id}"
                    )

        if result.confidence.overall < settings.consensus_threshold:
            report.weak_evidence.append(
                f"Overall confidence ({result.confidence.overall:.2f}) below threshold"
            )

        if report.weak_evidence:
            report.errors.append(
                f"Weak evidence detected: {len(report.weak_evidence)} items"
            )

    def _check_duplicate_insights(
        self,
        result: AnalysisResult,
        report: AnalysisValidationReport,
    ) -> None:
        seen: set[str] = set()
        for section in result.sections:
            for insight in section.insights:
                key = insight.insight[:80].lower()
                if key in seen:
                    report.duplicate_insights.append(insight.insight[:60])
                    report.warnings.append(f"Duplicate insight: {insight.insight[:60]}...")
                seen.add(key)

    def _check_contradictory_recommendations(
        self,
        result: AnalysisResult,
        report: AnalysisValidationReport,
    ) -> None:
        for i in range(len(result.recommendations)):
            for j in range(i + 1, len(result.recommendations)):
                r1 = result.recommendations[i].recommendation.lower()
                r2 = result.recommendations[j].recommendation.lower()
                if self._are_contradictory(r1, r2):
                    report.warnings.append(
                        f"Potentially contradictory recommendations: "
                        f"'{result.recommendations[i].recommendation[:40]}...' vs "
                        f"'{result.recommendations[j].recommendation[:40]}...'"
                    )

    def _check_citation_completeness(
        self,
        result: AnalysisResult,
        report: AnalysisValidationReport,
    ) -> None:
        for consensus in result.consensus:
            if not consensus.supporting_sources:
                report.warnings.append(
                    f"Consensus without sources: {consensus.statement[:60]}..."
                )
        for contradiction in result.contradictions:
            for side in contradiction.conflicting_sides:
                if not side.sources:
                    report.warnings.append(
                        f"Contradiction side without sources: {side.position[:60]}..."
                    )

    def _are_contradictory(self, r1: str, r2: str) -> bool:
        opposites = [
            ("increase", "decrease"),
            ("expand", "reduce"),
            ("more", "less"),
            ("larger", "smaller"),
            ("bigger", "smaller"),
        ]
        for a, b in opposites:
            if (a in r1 and b in r2) or (b in r1 and a in r2):
                return True
        return False
