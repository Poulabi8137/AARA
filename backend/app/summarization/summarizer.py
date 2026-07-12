from __future__ import annotations

import time

from app.core.logging import get_logger
from app.summarization.config import get_summarization_settings
from app.summarization.evidence_grouping import EvidenceGrouper
from app.summarization.finding_extractor import FindingExtractor
from app.summarization.gap_extractor import GapExtractor
from app.summarization.literature_review import LiteratureReviewSynthesizer
from app.summarization.models import (
    EvidenceGroup,
    ExtractedFinding,
    GroupingStrategy,
    ResearchGap,
    SummaryLevel,
    SummaryMetadata,
    SummaryRequest,
    SummaryResult,
    SummarySection,
    SummaryStatistics,
)
from app.summarization.multi_document import MultiDocumentSummarizer
from app.summarization.section_builder import SectionBuilder
from app.summarization.validator import SummaryValidator
from app.rag.context_builder import ContextBuilder
from app.rag.llm import RAGLLMProvider
from app.rag.retrieval_pipeline import RetrievalPipeline

logger = get_logger("summarization.orchestrator")
settings = get_summarization_settings()


class Summarizer:
    def __init__(
        self,
        retrieval_pipeline: RetrievalPipeline | None = None,
        context_builder: ContextBuilder | None = None,
        llm: RAGLLMProvider | None = None,
        evidence_grouper: EvidenceGrouper | None = None,
        multi_document: MultiDocumentSummarizer | None = None,
        section_builder: SectionBuilder | None = None,
        literature_review: LiteratureReviewSynthesizer | None = None,
        finding_extractor: FindingExtractor | None = None,
        gap_extractor: GapExtractor | None = None,
        validator: SummaryValidator | None = None,
    ):
        self._retrieval_pipeline = retrieval_pipeline
        self._context_builder = context_builder or ContextBuilder()
        self._llm = llm
        self._evidence_grouper = evidence_grouper or EvidenceGrouper()
        self._multi_document = multi_document
        self._section_builder = section_builder or SectionBuilder()
        self._literature_review = literature_review
        self._finding_extractor = finding_extractor
        self._gap_extractor = gap_extractor
        self._validator = validator or SummaryValidator()

    async def summarize(self, request: SummaryRequest) -> SummaryResult:
        start = time.monotonic()

        groups = await self._retrieve_and_group(request)

        content, sections = await self._generate_summary(request, groups)

        findings = await self._extract_findings(request, groups)

        gaps = await self._extract_gaps(request, groups)

        level = (
            request.level
            if isinstance(request.level, SummaryLevel)
            else SummaryLevel.STANDARD
        )
        stats = self._build_statistics(groups, sections, findings, gaps)
        validation = self._validator.validate(
            SummaryResult(
                summary=content,
                sections=sections,
                findings=findings,
                gaps=gaps,
                groups=groups,
                statistics=stats,
            ),
            groups,
        )
        metadata = SummaryMetadata(
            duration_ms=round((time.monotonic() - start) * 1000, 1),
            level=level,
            model=settings.model,
            validation_passed=validation.is_valid,
            validation_errors=validation.errors,
        )

        logger.info(
            "summarization complete",
            extra={
                "level": level.value,
                "sections": len(sections),
                "findings": len(findings),
                "gaps": len(gaps),
                "groups": len(groups),
                "valid": validation.is_valid,
                "duration_ms": metadata.duration_ms,
            },
        )

        return SummaryResult(
            summary=content,
            sections=sections,
            findings=findings,
            gaps=gaps,
            groups=groups,
            statistics=stats,
            metadata=metadata,
            validation=validation,
        )

    async def _retrieve_and_group(
        self,
        request: SummaryRequest,
    ) -> list[EvidenceGroup]:
        evidence = request.evidence
        if not evidence and self._retrieval_pipeline:
            raise NotImplementedError(
                "Automatic retrieval from pipeline not yet implemented; pass evidence directly"
            )
        if not evidence:
            logger.warning("no evidence provided for summarization")
            return []

        strategy = (
            request.grouping
            if isinstance(request.grouping, GroupingStrategy)
            else GroupingStrategy.TOPIC
        )
        return self._evidence_grouper.group(evidence, strategy)

    async def _generate_summary(
        self,
        request: SummaryRequest,
        groups: list[EvidenceGroup],
    ) -> tuple[str, list[SummarySection]]:
        level = (
            request.level
            if isinstance(request.level, SummaryLevel)
            else SummaryLevel.STANDARD
        )

        if level == SummaryLevel.LITERATURE_REVIEW and self._literature_review:
            content, sections, _, _ = await self._literature_review.synthesize(
                request, groups
            )
            return content, sections

        if self._multi_document:
            return await self._multi_document.summarize(request, groups)

        return "", []

    async def _extract_findings(
        self,
        request: SummaryRequest,
        groups: list[EvidenceGroup],
    ) -> list[ExtractedFinding]:
        if not self._finding_extractor:
            return []
        return await self._finding_extractor.extract(request.query, groups)

    async def _extract_gaps(
        self,
        request: SummaryRequest,
        groups: list[EvidenceGroup],
    ) -> list[ResearchGap]:
        if not self._gap_extractor:
            return []
        return await self._gap_extractor.extract(request.query, groups)

    def _build_statistics(
        self,
        groups: list[EvidenceGroup],
        sections: list[SummarySection],
        findings: list[ExtractedFinding],
        gaps: list[ResearchGap],
    ) -> SummaryStatistics:
        total_sources = sum(len(g.evidence) for g in groups)
        evidence_by_type: dict[str, int] = {}
        for g in groups:
            for ev in g.evidence:
                st = ev.source_type.value
                evidence_by_type[st] = evidence_by_type.get(st, 0) + 1

        all_citations: set[str] = set()
        for s in sections:
            all_citations.update(s.citations)
        for f in findings:
            all_citations.update(f.citations)

        return SummaryStatistics(
            total_sources=total_sources,
            total_citations=len(all_citations),
            total_sections=len(sections),
            total_findings=len(findings),
            total_gaps=len(gaps),
            total_tokens=sum(len(s.content.split()) for s in sections),
            evidence_by_type=evidence_by_type,
        )
