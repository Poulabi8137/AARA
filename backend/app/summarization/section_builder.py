from __future__ import annotations

from app.core.logging import get_logger
from app.summarization.config import get_summarization_settings
from app.summarization.models import (
    SectionType,
    SummaryChunk,
    SummaryLevel,
    SummarySection,
)

logger = get_logger("summarization.section_builder")
settings = get_summarization_settings()

_DEFAULT_SECTION_ORDER: list[SectionType] = [
    SectionType.ABSTRACT,
    SectionType.BACKGROUND,
    SectionType.PROBLEM_STATEMENT,
    SectionType.METHODOLOGY,
    SectionType.EXPERIMENTAL_SETUP,
    SectionType.RESULTS,
    SectionType.DISCUSSION,
    SectionType.LIMITATIONS,
    SectionType.FUTURE_WORK,
    SectionType.CONCLUSION,
]

_LEVEL_SECTIONS: dict[SummaryLevel, list[SectionType]] = {
    SummaryLevel.BRIEF: [
        SectionType.ABSTRACT,
        SectionType.CONCLUSION,
    ],
    SummaryLevel.STANDARD: [
        SectionType.ABSTRACT,
        SectionType.BACKGROUND,
        SectionType.METHODOLOGY,
        SectionType.RESULTS,
        SectionType.DISCUSSION,
        SectionType.CONCLUSION,
    ],
    SummaryLevel.DETAILED: list(_DEFAULT_SECTION_ORDER),
    SummaryLevel.LITERATURE_REVIEW: [
        SectionType.ABSTRACT,
        SectionType.BACKGROUND,
        SectionType.METHODOLOGY,
        SectionType.RESULTS,
        SectionType.DISCUSSION,
        SectionType.LIMITATIONS,
        SectionType.FUTURE_WORK,
        SectionType.CONCLUSION,
    ],
    SummaryLevel.EXECUTIVE_SUMMARY: [
        SectionType.ABSTRACT,
        SectionType.CONCLUSION,
    ],
}


class SectionBuilder:
    def build_sections(
        self,
        level: SummaryLevel,
        sections_override: list[SectionType] | None = None,
    ) -> list[SectionType]:
        if sections_override:
            return sections_override
        return _LEVEL_SECTIONS.get(level, _DEFAULT_SECTION_ORDER)

    def build_chunk(
        self,
        content: str,
        section: SectionType,
        citations: list[str],
        confidence: float = 1.0,
        source_ids: list[str] | None = None,
    ) -> SummaryChunk:
        return SummaryChunk(
            content=content,
            section=section,
            citations=citations,
            confidence=confidence,
            source_ids=source_ids or [],
        )

    def build_section(
        self,
        section_type: SectionType,
        title: str,
        content: str,
        chunks: list[SummaryChunk] | None = None,
        evidence_count: int = 0,
        citations: list[str] | None = None,
    ) -> SummarySection:
        return SummarySection(
            type=section_type,
            title=title,
            content=content,
            chunks=chunks or [],
            evidence_count=evidence_count,
            citations=citations or [],
        )
