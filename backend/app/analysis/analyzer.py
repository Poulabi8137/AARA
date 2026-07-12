from __future__ import annotations

import time

from app.analysis.config import get_analysis_settings
from app.analysis.consensus import ConsensusDetector
from app.analysis.contradiction import ContradictionDetector
from app.analysis.trends import TrendAnalyzer
from app.analysis.limitations import LimitationAnalyzer
from app.analysis.recommendations import RecommendationEngine
from app.analysis.confidence import ConfidenceAssessor
from app.analysis.relationships import RelationshipBuilder
from app.analysis.validator import AnalysisValidator
from app.analysis.models import (
    AnalysisInsight,
    AnalysisMetadata,
    AnalysisRequest,
    AnalysisResult,
    AnalysisSection,
    AnalysisSectionType,
    AnalysisStatistics,
    AnalysisValidationReport,
    ConfidenceAssessment,
)
from app.core.logging import get_logger
from app.rag.llm import RAGLLMProvider
from app.summarization.models import EvidenceGroup, SummaryResult

logger = get_logger("analysis.orchestrator")
settings = get_analysis_settings()


class Analyzer:
    def __init__(
        self,
        llm: RAGLLMProvider | None = None,
        consensus_detector: ConsensusDetector | None = None,
        contradiction_detector: ContradictionDetector | None = None,
        trend_analyzer: TrendAnalyzer | None = None,
        limitation_analyzer: LimitationAnalyzer | None = None,
        recommendation_engine: RecommendationEngine | None = None,
        confidence_assessor: ConfidenceAssessor | None = None,
        relationship_builder: RelationshipBuilder | None = None,
        validator: AnalysisValidator | None = None,
    ):
        self._llm = llm
        self._consensus = consensus_detector or ConsensusDetector(llm)
        self._contradiction = contradiction_detector or ContradictionDetector(llm)
        self._trends = trend_analyzer or TrendAnalyzer(llm)
        self._limitations = limitation_analyzer or LimitationAnalyzer(llm)
        self._recommendations = recommendation_engine or RecommendationEngine(llm)
        self._confidence = confidence_assessor or ConfidenceAssessor()
        self._relationships = relationship_builder or RelationshipBuilder()
        self._validator = validator or AnalysisValidator()

    async def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        start = time.monotonic()

        groups = self._extract_groups(request)
        section_types = request.section_types or list(AnalysisSectionType)

        consensus: list = []
        contradictions: list = []
        trends: list = []
        limitations: list = []
        recommendations: list = []
        relationships: list = []
        sections: list[AnalysisSection] = []

        if AnalysisSectionType.CONSENSUS in section_types or not section_types:
            consensus = await self._consensus.detect(request.query, groups)
            sections.append(self._build_section(
                AnalysisSectionType.CONSENSUS, "Consensus Analysis", consensus,
            ))

        if AnalysisSectionType.CONTRADICTION in section_types or not section_types:
            contradictions = await self._contradiction.detect(request.query, groups)
            sections.append(self._build_section(
                AnalysisSectionType.CONTRADICTION, "Contradiction Analysis", contradictions,
            ))

        if AnalysisSectionType.TRENDS in section_types or not section_types:
            trends = await self._trends.analyze(request.query, groups)
            sections.append(self._build_section(
                AnalysisSectionType.TRENDS, "Trend Analysis", trends,
            ))

        if AnalysisSectionType.LIMITATIONS in section_types or not section_types:
            limitations = await self._limitations.analyze(request.query, groups)
            sections.append(self._build_section(
                AnalysisSectionType.LIMITATIONS, "Limitation Analysis", limitations,
            ))

        if AnalysisSectionType.RECOMMENDATIONS in section_types or not section_types:
            recommendations = await self._recommendations.generate(request.query, groups)
            sections.append(self._build_section(
                AnalysisSectionType.RECOMMENDATIONS, "Recommendations", recommendations,
            ))

        confidence = self._confidence.assess(
            groups,
            consensus_count=len(consensus),
            contradiction_count=len(contradictions),
        )
        sections.append(self._build_confidence_section(confidence))

        if AnalysisSectionType.RELATIONSHIPS in section_types or not section_types:
            relationships = self._relationships.build(groups)
            sections.append(self._build_section(
                AnalysisSectionType.RELATIONSHIPS, "Evidence Relationships", relationships,
            ))

        stats = self._build_statistics(
            consensus, contradictions, trends, limitations, recommendations,
            relationships, confidence,
        )

        result = AnalysisResult(
            sections=sections,
            consensus=consensus,
            contradictions=contradictions,
            trends=trends,
            limitations=limitations,
            recommendations=recommendations,
            confidence=confidence,
            relationships=relationships,
            statistics=stats,
        )

        validation = self._validator.validate(result, groups)
        duration = time.monotonic() - start

        metadata = AnalysisMetadata(
            duration_ms=round(duration * 1000, 1),
            model=settings.model,
            validation_passed=validation.is_valid,
            validation_errors=validation.errors,
        )
        result.metadata = metadata
        result.validation = validation

        logger.info(
            "analysis complete",
            extra={
                "sections": len(sections),
                "consensus": len(consensus),
                "contradictions": len(contradictions),
                "trends": len(trends),
                "limitations": len(limitations),
                "recommendations": len(recommendations),
                "relationships": len(relationships),
                "confidence": confidence.overall,
                "valid": validation.is_valid,
                "duration_ms": metadata.duration_ms,
            },
        )

        return result

    def _extract_groups(self, request: AnalysisRequest) -> list[EvidenceGroup]:
        sr = request.summary_result
        if hasattr(sr, "groups") and sr.groups:
            return sr.groups
        if hasattr(sr, "evidence") and sr.evidence:
            from app.summarization.evidence_grouping import EvidenceGrouper
            grouper = EvidenceGrouper()
            return grouper.group(sr.evidence)
        return []

    def _build_section(
        self,
        st: AnalysisSectionType,
        title: str,
        items: list,
    ) -> AnalysisSection:
        insights = []
        for item in items:
            label = ""
            if hasattr(item, "statement"):
                label = item.statement
            elif hasattr(item, "trend"):
                label = item.trend
            elif hasattr(item, "limitation"):
                label = item.limitation
            elif hasattr(item, "recommendation"):
                label = item.recommendation
            elif hasattr(item, "source_id") and hasattr(item, "target_id"):
                label = f"{item.source_id} -> {item.target_id} ({item.relationship_type})"
            if label:
                insights.append(AnalysisInsight(
                    insight=str(label)[:200],
                    evidence=[],
                    confidence=getattr(item, "confidence", 0.5),
                    category=getattr(item, "category", "general"),
                ))

        content = "\n".join(i.insight for i in insights)
        return AnalysisSection(
            type=st,
            title=title,
            content=content[:2000],
            insights=insights,
        )

    def _build_confidence_section(
        self, confidence: ConfidenceAssessment
    ) -> AnalysisSection:
        lines = [
            f"Overall Confidence: {confidence.overall:.2%}",
            f"Evidence Quality: {confidence.evidence_quality:.2%}",
            f"Citation Support: {confidence.citation_support:.2%}",
            f"Agreement Level: {confidence.agreement_level:.2%}",
            f"Publication Diversity: {confidence.publication_diversity:.2%}",
            f"Retrieval Confidence: {confidence.retrieval_confidence:.2%}",
        ]
        return AnalysisSection(
            type=AnalysisSectionType.CONFIDENCE,
            title="Confidence Assessment",
            content="\n".join(lines),
            insights=[],
        )

    def _build_statistics(
        self,
        consensus: list,
        contradictions: list,
        trends: list,
        limitations: list,
        recommendations: list,
        relationships: list,
        confidence: ConfidenceAssessment,
    ) -> AnalysisStatistics:
        return AnalysisStatistics(
            total_consensus=len(consensus),
            total_contradictions=len(contradictions),
            total_trends=len(trends),
            total_limitations=len(limitations),
            total_recommendations=len(recommendations),
            total_relationships=len(relationships),
            overall_confidence=confidence.overall,
        )
