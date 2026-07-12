from __future__ import annotations

import re
import time

from app.core.logging import get_logger
from app.summarization.config import get_summarization_settings
from app.summarization.models import EvidenceGroup, ExtractedFinding
from app.rag.llm import RAGLLMProvider

logger = get_logger("summarization.finding_extractor")
settings = get_summarization_settings()

_FINDING_SYSTEM: str = (
    "You are a research finding extraction assistant. "
    "Extract key findings and insights from the provided research evidence. "
    "For each finding, provide:\n"
    "- The finding statement\n"
    "- Supporting citation keys\n"
    "- Confidence level (high/medium/low)\n"
    "- Category (methodology, result, comparison, limitation, application, trend)\n\n"
    "Format each finding as:\n"
    "Finding: <statement>\n"
    "Citations: [1], [2]\n"
    "Confidence: high|medium|low\n"
    "Category: <category>"
)

_FINDING_USER: str = (
    "Research Topic: {query}\n\n"
    "Evidence Groups:\n{groups}\n\n"
    "Extract up to {max_findings} key findings from the evidence above."
)


class FindingExtractor:
    def __init__(self, llm: RAGLLMProvider):
        self._llm = llm

    async def extract(
        self,
        query: str,
        groups: list[EvidenceGroup],
    ) -> list[ExtractedFinding]:
        start = time.monotonic()
        groups_text = self._format_groups(groups)

        content = await self._llm.generate(
            prompt=_FINDING_USER.format(
                query=query,
                groups=groups_text,
                max_findings=settings.max_findings,
            ),
            system_prompt=_FINDING_SYSTEM,
            temperature=0.2,
            max_tokens=settings.max_tokens,
        )

        findings = self._parse_findings(content)

        logger.info(
            "finding extraction complete",
            extra={
                "findings": len(findings),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return findings

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

    def _parse_findings(self, content: str) -> list[ExtractedFinding]:
        findings: list[ExtractedFinding] = []
        blocks = re.split(r"\n\s*\n", content)
        current: dict = {}

        for block in blocks:
            block = block.strip()
            if not block:
                continue
            if block.lower().startswith("finding:"):
                if current.get("finding"):
                    findings.append(self._build_finding(current))
                current = {"finding": block.split(":", 1)[1].strip()}
            elif block.lower().startswith("citations:"):
                citations = re.findall(r"\[\d+\]", block)
                current["citations"] = citations
            elif block.lower().startswith("confidence:"):
                conf_str = block.split(":", 1)[1].strip().lower()
                current["confidence"] = (
                    0.9
                    if conf_str == "high"
                    else (0.5 if conf_str == "medium" else 0.2)
                )
            elif block.lower().startswith("category:"):
                current["category"] = block.split(":", 1)[1].strip()

        if current.get("finding"):
            findings.append(self._build_finding(current))

        return findings[: settings.max_findings]

    def _build_finding(self, data: dict) -> ExtractedFinding:
        return ExtractedFinding(
            finding=data.get("finding", ""),
            supporting_evidence=[],
            confidence=data.get("confidence", 0.5),
            citations=data.get("citations", []),
            category=data.get("category", "general"),
        )
