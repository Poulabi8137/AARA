from __future__ import annotations

import time
import re

from app.core.logging import get_logger
from app.summarization.config import get_summarization_settings
from app.summarization.models import (
    EvidenceGroup,
    ExtractedFinding,
    ResearchGap,
    SummaryRequest,
    SummarySection,
    SectionType,
)
from app.rag.llm import RAGLLMProvider

logger = get_logger("summarization.literature_review")
settings = get_summarization_settings()

_LITERATURE_REVIEW_SYSTEM: str = (
    "You are a literature review synthesis assistant. "
    "Analyze the provided research evidence and generate a structured literature review. "
    "Focus on:\n"
    "1. Common themes across the literature\n"
    "2. Areas of consensus among researchers\n"
    "3. Disagreements or conflicting findings\n"
    "4. Research trends and trajectories\n"
    "5. Identified research gaps\n"
    "6. Open questions requiring further investigation\n\n"
    "Cite all sources using citation keys like [1], [2]. "
    "Be specific and evidence-based in your analysis."
)

_LITERATURE_REVIEW_USER: str = (
    "Research Topic: {query}\n\n"
    "Evidence Groups:\n{groups}\n\n"
    "Generate a comprehensive literature review addressing:\n"
    "- Themes: What are the major themes in this research area?\n"
    "- Consensus: Where do researchers broadly agree?\n"
    "- Disagreements: Where are there conflicting findings or interpretations?\n"
    "- Trends: What research trends are visible in recent work?\n"
    "- Gaps: What important questions remain unanswered?\n"
    "Use citation keys to reference specific sources."
)


class LiteratureReviewSynthesizer:
    def __init__(self, llm: RAGLLMProvider):
        self._llm = llm

    async def synthesize(
        self,
        request: SummaryRequest,
        groups: list[EvidenceGroup],
    ) -> tuple[str, list[SummarySection], list[ExtractedFinding], list[ResearchGap]]:
        start = time.monotonic()
        groups_text = self._format_groups(groups)

        content = await self._llm.generate(
            prompt=_LITERATURE_REVIEW_USER.format(
                query=request.query,
                groups=groups_text,
            ),
            system_prompt=_LITERATURE_REVIEW_SYSTEM,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )

        findings = self._extract_findings(content)
        gaps = self._extract_gaps(content)

        section = SummarySection(
            type=SectionType.ABSTRACT,
            title="Literature Review",
            content=content,
            evidence_count=sum(len(g.evidence) for g in groups),
            citations=re.findall(r"\[\d+\]", content),
        )

        logger.info(
            "literature review synthesis complete",
            extra={
                "groups": len(groups),
                "findings": len(findings),
                "gaps": len(gaps),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )

        return content, [section], findings, gaps

    def _format_groups(self, groups: list[EvidenceGroup]) -> str:
        parts: list[str] = []
        for i, group in enumerate(groups, 1):
            header = f"Group {i}: {group.label}"
            texts: list[str] = []
            for j, ev in enumerate(group.evidence):
                key = (
                    group.citation_keys[j]
                    if j < len(group.citation_keys)
                    else f"[{j + 1}]"
                )
                texts.append(f"{key} {ev.content[:500]}")
            parts.append(f"{header}\n" + "\n".join(texts))
        return "\n\n".join(parts)

    def _extract_findings(self, content: str) -> list[ExtractedFinding]:
        findings: list[ExtractedFinding] = []
        lines = content.split("\n")
        for line in lines:
            lower = line.lower().strip()
            if any(
                kw in lower for kw in ["finding:", "key finding:", "major finding:"]
            ):
                citations = re.findall(r"\[\d+\]", line)
                findings.append(
                    ExtractedFinding(
                        finding=line.split(":", 1)[1].strip()
                        if ":" in line
                        else line.strip(),
                        citations=citations,
                        category="extracted",
                    )
                )
        return findings[: settings.max_findings]

    def _extract_gaps(self, content: str) -> list[ResearchGap]:
        gaps: list[ResearchGap] = []
        lines = content.split("\n")
        for line in lines:
            lower = line.lower().strip()
            if any(
                kw in lower
                for kw in ["gap:", "research gap:", "open question:", "unanswered:"]
            ):
                gap_type = "unanswered_question"
                if "conflicting" in lower or "disagreement" in lower:
                    gap_type = "conflicting_finding"
                elif "insufficient" in lower or "limited" in lower:
                    gap_type = "insufficient_evidence"
                elif "underexplored" in lower or "unexplored" in lower:
                    gap_type = "underexplored_topic"
                gaps.append(
                    ResearchGap(
                        gap=line.split(":", 1)[1].strip()
                        if ":" in line
                        else line.strip(),
                        gap_type=gap_type,
                    )
                )
        return gaps[: settings.max_gaps]
