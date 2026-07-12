from __future__ import annotations

import time

from app.core.logging import get_logger
from app.analysis.config import get_analysis_settings
from app.analysis.models import ConfidenceAssessment
from app.summarization.models import EvidenceGroup

logger = get_logger("analysis.confidence")
settings = get_analysis_settings()


class ConfidenceAssessor:
    def assess(
        self,
        groups: list[EvidenceGroup],
        consensus_count: int = 0,
        contradiction_count: int = 0,
    ) -> ConfidenceAssessment:
        start = time.monotonic()

        weights = self._parse_weights()

        evidence_quality = self._score_evidence_quality(groups)
        citation_support = self._score_citation_support(groups)
        agreement_level = self._score_agreement(consensus_count, contradiction_count)
        publication_diversity = self._score_diversity(groups)
        retrieval_conf = self._score_retrieval_confidence(groups)

        overall = (
            weights[0] * evidence_quality
            + weights[1] * citation_support
            + weights[2] * agreement_level
            + weights[3] * publication_diversity
            + weights[4] * retrieval_conf
        )

        result = ConfidenceAssessment(
            overall=round(overall, 4),
            evidence_quality=round(evidence_quality, 4),
            citation_support=round(citation_support, 4),
            agreement_level=round(agreement_level, 4),
            publication_diversity=round(publication_diversity, 4),
            retrieval_confidence=round(retrieval_conf, 4),
        )

        logger.info(
            "confidence assessment complete",
            extra={
                "overall": result.overall,
                "evidence_quality": result.evidence_quality,
                "citation_support": result.citation_support,
                "agreement_level": result.agreement_level,
                "diversity": result.publication_diversity,
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return result

    def _parse_weights(self) -> list[float]:
        parts = settings.confidence_weights.split(",")
        weights = []
        for p in parts:
            try:
                weights.append(float(p.strip()))
            except (ValueError, TypeError):
                weights.append(0.2)
        while len(weights) < 5:
            weights.append(0.2)
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]
        return weights[:5]

    def _score_evidence_quality(self, groups: list[EvidenceGroup]) -> float:
        scores: list[float] = []
        for group in groups:
            for ev in group.evidence:
                scores.append(max(0.0, ev.score))
        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    def _score_citation_support(self, groups: list[EvidenceGroup]) -> float:
        total = 0
        cited = 0
        for group in groups:
            for ev in group.evidence:
                total += 1
                has_citation = bool(
                    ev.metadata.get("title")
                    or ev.metadata.get("doi")
                    or ev.metadata.get("source")
                    or ev.provenance
                )
                if has_citation:
                    cited += 1
        if total == 0:
            return 0.0
        return cited / total

    def _score_agreement(
        self, consensus_count: int, contradiction_count: int
    ) -> float:
        total = consensus_count + contradiction_count
        if total == 0:
            return 0.5
        score = consensus_count / total if total > 0 else 0.5
        return min(1.0, score * 1.2)

    def _score_diversity(self, groups: list[EvidenceGroup]) -> float:
        all_sources: set[str] = set()
        total_items = 0
        for group in groups:
            for ev in group.evidence:
                all_sources.add(ev.source_type.value)
                total_items += 1
        if total_items == 0:
            return 0.0
        return min(1.0, len(all_sources) / max(1, total_items) * 3)

    def _score_retrieval_confidence(self, groups: list[EvidenceGroup]) -> float:
        scores: list[float] = []
        for group in groups:
            for ev in group.evidence:
                meta_conf = ev.metadata.get("confidence", None)
                if meta_conf is not None:
                    try:
                        scores.append(float(meta_conf))
                    except (ValueError, TypeError):
                        scores.append(ev.score)
                else:
                    scores.append(ev.score)
        if not scores:
            return 0.0
        return sum(scores) / len(scores)
