from __future__ import annotations

import time

from app.core.logging import get_logger
from app.summarization.config import get_summarization_settings
from app.summarization.models import (
    EvidenceGroup,
    SummaryLevel,
    SummaryRequest,
    SummarySection,
    SectionType,
)
from app.rag.llm import RAGLLMProvider
from app.rag.context_builder import ContextBuilder

logger = get_logger("summarization.multi_document")
settings = get_summarization_settings()

_LEVEL_SYSTEM_PROMPTS: dict[str, str] = {
    "brief": (
        "You are a precise research summarization assistant. "
        "Generate a concise brief summary of the provided research evidence. "
        "Focus on the most important findings only. Use 2-3 paragraphs maximum. "
        "Cite sources inline using citation keys like [1], [2]."
    ),
    "standard": (
        "You are a research summarization assistant. "
        "Generate a structured summary of the provided research evidence. "
        "Organize the summary by key themes or findings. "
        "Include citations for each major point using citation keys like [1], [2]. "
        "Aim for 4-6 paragraphs covering the main contributions."
    ),
    "detailed": (
        "You are a comprehensive research summarization assistant. "
        "Generate a detailed, well-structured summary of the provided research evidence. "
        "Cover methodology, results, analysis, and conclusions. "
        "Cite all sources using citation keys like [1], [2]. "
        "Aim for 8-12 paragraphs with thorough coverage."
    ),
    "literature_review": (
        "You are a literature review synthesis assistant. "
        "Generate a comprehensive literature review from the provided evidence. "
        "Organize by themes and approaches. Identify areas of consensus and disagreement. "
        "Cite all sources using citation keys like [1], [2]. "
        "Include a summary of key findings and open questions."
    ),
    "executive_summary": (
        "You are an executive research summarization assistant. "
        "Generate a high-level executive summary of the provided research evidence. "
        "Focus on strategic insights, key findings, and actionable conclusions. "
        "Use concise business-friendly language. Cite sources using citation keys like [1], [2]. "
        "Aim for 3-5 paragraphs."
    ),
}

_SECTION_PROMPT_TEMPLATE: str = (
    "Generate the '{section}' section of a research summary on the topic: {query}.\n\n"
    "Use the following evidence groups:\n{groups}\n\n"
    "Requirements:\n"
    "- Write 2-4 paragraphs\n"
    "- Cite sources using citation keys like [1], [2]\n"
    "- Focus only on the {section} aspect\n"
    "Section:"
)

_FULL_SUMMARY_SYSTEM: str = (
    "You are a research summarization assistant. "
    "Generate a comprehensive, well-structured research summary from the provided evidence groups. "
    "Organize the summary thematically. Preserve all source citations. "
    "Use citation keys like [1], [2] to reference sources. "
    "Aim for completeness and accuracy."
)


class MultiDocumentSummarizer:
    def __init__(
        self,
        llm: RAGLLMProvider,
        context_builder: ContextBuilder | None = None,
    ):
        self._llm = llm
        self._context_builder = context_builder or ContextBuilder()

    async def summarize(
        self,
        request: SummaryRequest,
        groups: list[EvidenceGroup],
    ) -> tuple[str, list[SummarySection]]:
        start = time.monotonic()

        groups_text = self._format_groups(groups)
        level = (
            request.level.value
            if isinstance(request.level, SummaryLevel)
            else request.level
        )

        if request.sections and len(request.sections) > 1:
            sections = await self._build_by_section(request, groups_text, groups)
        else:
            sections = await self._build_single_summary(
                request, groups_text, groups, level
            )

        logger.info(
            "multi-document summarization complete",
            extra={
                "level": level,
                "groups": len(groups),
                "sections": len(sections),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return self._merge_sections(sections), sections

    async def _build_single_summary(
        self,
        request: SummaryRequest,
        groups_text: str,
        groups: list[EvidenceGroup],
        level: str,
    ) -> list[SummarySection]:
        system_prompt = _LEVEL_SYSTEM_PROMPTS.get(
            level, _LEVEL_SYSTEM_PROMPTS["standard"]
        )
        user_prompt = (
            f"Research Topic: {request.query}\n\n"
            f"Evidence Groups:\n{groups_text}\n\n"
            f"Generate a {level} research summary. "
            "Use citation keys like [1], [2] to reference sources. "
            "Include all major findings from the evidence."
        )

        content = await self._llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )

        section = SummarySection(
            type=SectionType.ABSTRACT,
            title="Summary",
            content=content,
            evidence_count=sum(len(g.evidence) for g in groups),
            citations=self._extract_citations(content),
        )
        return [section]

    async def _build_by_section(
        self,
        request: SummaryRequest,
        groups_text: str,
        groups: list[EvidenceGroup],
    ) -> list[SummarySection]:
        sections: list[SummarySection] = []
        for st in request.sections:
            section_title = st.value.replace("_", " ").title()
            prompt = _SECTION_PROMPT_TEMPLATE.format(
                section=section_title,
                query=request.query,
                groups=groups_text,
            )

            content = await self._llm.generate(
                prompt=prompt,
                system_prompt=_FULL_SUMMARY_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )

            sections.append(
                SummarySection(
                    type=st,
                    title=section_title,
                    content=content,
                    evidence_count=sum(len(g.evidence) for g in groups),
                    citations=self._extract_citations(content),
                )
            )

        return sections

    def _format_groups(self, groups: list[EvidenceGroup]) -> str:
        parts: list[str] = []
        for i, group in enumerate(groups, 1):
            header = f"Group {i}: {group.label}"
            evidence_texts: list[str] = []
            for j, ev in enumerate(group.evidence):
                citation = (
                    group.citation_keys[j]
                    if j < len(group.citation_keys)
                    else f"[{j + 1}]"
                )
                text = f"{citation} {ev.content[:500]}"
                evidence_texts.append(text)
            parts.append(f"{header}\n" + "\n".join(evidence_texts))
        return "\n\n".join(parts)

    def _extract_citations(self, text: str) -> list[str]:
        import re

        return re.findall(r"\[\d+\]", text)

    def _merge_sections(self, sections: list[SummarySection]) -> str:
        return "\n\n".join(f"## {s.title}\n{s.content}" for s in sections)
