from __future__ import annotations

import re
import time

from app.core.logging import get_logger
from app.summarization.config import get_summarization_settings
from app.summarization.models import EvidenceGroup, ResearchGap
from app.rag.llm import RAGLLMProvider

logger = get_logger("summarization.gap_extractor")
settings = get_summarization_settings()

_GAP_SYSTEM: str = (
    "You are a research gap analysis assistant. "
    "Identify potential research gaps from the provided evidence. "
    "Gap types:\n"
    "- unanswered_question: Important questions not addressed\n"
    "- insufficient_evidence: Claims made with limited supporting evidence\n"
    "- conflicting_finding: Directly contradictory results across sources\n"
    "- underexplored_topic: Areas with very few sources or shallow coverage\n\n"
    "Format each gap as:\n"
    "Gap: <description>\n"
    "Type: unanswered_question|insufficient_evidence|conflicting_finding|underexplored_topic\n"
    "Evidence: [1], [2]"
)

_GAP_USER: str = (
    "Research Topic: {query}\n\n"
    "Evidence Groups:\n{groups}\n\n"
    "Identify up to {max_gaps} research gaps from the evidence above."
)


class GapExtractor:
    def __init__(self, llm: RAGLLMProvider):
        self._llm = llm

    async def extract(
        self,
        query: str,
        groups: list[EvidenceGroup],
    ) -> list[ResearchGap]:
        start = time.monotonic()
        groups_text = self._format_groups(groups)

        content = await self._llm.generate(
            prompt=_GAP_USER.format(
                query=query,
                groups=groups_text,
                max_gaps=settings.max_gaps,
            ),
            system_prompt=_GAP_SYSTEM,
            temperature=0.2,
            max_tokens=settings.max_tokens,
        )

        gaps = self._parse_gaps(content)

        logger.info(
            "gap extraction complete",
            extra={
                "gaps": len(gaps),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return gaps

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
                texts.append(f"{key} {ev.content[:400]}")
            parts.append(f"{header}\n" + "\n".join(texts))
        return "\n\n".join(parts)

    def _parse_gaps(self, content: str) -> list[ResearchGap]:
        gaps: list[ResearchGap] = []
        blocks = re.split(r"\n\s*\n", content)
        current: dict = {}

        for block in blocks:
            block = block.strip()
            if not block:
                continue
            if block.lower().startswith("gap:"):
                if current.get("gap"):
                    gaps.append(self._build_gap(current))
                current = {"gap": block.split(":", 1)[1].strip()}
            elif block.lower().startswith("type:"):
                current["type"] = block.split(":", 1)[1].strip()
            elif block.lower().startswith("evidence:"):
                current["evidence"] = re.findall(r"\[\d+\]", block)

        if current.get("gap"):
            gaps.append(self._build_gap(current))

        return gaps[: settings.max_gaps]

    def _build_gap(self, data: dict) -> ResearchGap:
        return ResearchGap(
            gap=data.get("gap", ""),
            evidence=data.get("evidence", []),
            gap_type=data.get("type", "unanswered_question"),
        )
