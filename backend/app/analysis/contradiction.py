from __future__ import annotations

import time
import re

from app.core.logging import get_logger
from app.analysis.config import get_analysis_settings
from app.analysis.models import ConflictingSide, Contradiction
from app.rag.llm import RAGLLMProvider
from app.summarization.models import EvidenceGroup

logger = get_logger("analysis.contradiction")
settings = get_analysis_settings()

_CONTRADICTION_SYSTEM: str = (
    "You are a research contradiction detection assistant. "
    "Analyze the provided evidence groups and identify conflicting findings, "
    "incompatible methodologies, or contradictory conclusions across sources.\n\n"
    "For each contradiction:\n"
    "- State the contradiction clearly\n"
    "- Describe each side with its supporting sources\n"
    "- Note any methodological differences that may explain the contradiction\n"
    "- Rate severity: high|medium|low\n\n"
    "Format:\n"
    "Contradiction: <statement>\n"
    "Side A: <position> | Sources: [1], [3]\n"
    "Side B: <position> | Sources: [2], [4]\n"
    "Severity: high|medium|low"
)

_CONTRADICTION_USER: str = (
    "Research Topic: {query}\n\n"
    "Evidence Groups:\n{groups}\n\n"
    "Identify up to {max} contradictions or conflicting findings in the evidence."
)


class ContradictionDetector:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def detect(
        self,
        query: str,
        groups: list[EvidenceGroup],
    ) -> list[Contradiction]:
        start = time.monotonic()

        if not self._llm or not settings.enable_llm_analysis:
            logger.info("LLM analysis disabled, skipping contradiction detection")
            return []

        groups_text = self._format_groups(groups)
        try:
            content = await self._llm.generate(
                prompt=_CONTRADICTION_USER.format(
                    query=query,
                    groups=groups_text,
                    max=settings.max_contradictions,
                ),
                system_prompt=_CONTRADICTION_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            contradictions = self._parse_contradictions(content)
        except Exception as exc:
            logger.warning("contradiction detection failed", extra={"error": str(exc)})
            contradictions = []

        logger.info(
            "contradiction detection complete",
            extra={
                "contradictions": len(contradictions),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return contradictions[: settings.max_contradictions]

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

    def _parse_contradictions(self, content: str) -> list[Contradiction]:
        results: list[Contradiction] = []
        blocks = re.split(r"\n\s*\n", content)
        current: dict = {}
        for block in blocks:
            block = block.strip()
            low = block.lower()
            if low.startswith("contradiction:"):
                if current.get("statement"):
                    results.append(self._build_contradiction(current))
                current = {"statement": block.split(":", 1)[1].strip()}
            elif low.startswith("side a:"):
                current["side_a"] = self._parse_side(block)
            elif low.startswith("side b:"):
                current["side_b"] = self._parse_side(block)
            elif low.startswith("severity:"):
                current["severity"] = block.split(":", 1)[1].strip().lower()
        if current.get("statement"):
            results.append(self._build_contradiction(current))
        return results

    def _parse_side(self, block: str) -> dict:
        parts = block.split("|")
        result: dict = {
            "position": parts[0].split(":", 1)[1].strip()
            if ":" in parts[0]
            else parts[0].strip()
        }
        for part in parts[1:]:
            if "sources:" in part.lower():
                result["sources"] = re.findall(r"\[\d+\]", part)
            if "methodology:" in part.lower():
                result["methodology"] = part.split(":", 1)[1].strip()
        return result

    def _build_contradiction(self, data: dict) -> Contradiction:
        sides: list[ConflictingSide] = []
        for key in ["side_a", "side_b"]:
            side_data = data.get(key)
            if side_data:
                sides.append(
                    ConflictingSide(
                        position=side_data.get("position", ""),
                        sources=side_data.get("sources", []),
                        methodology=side_data.get("methodology"),
                    )
                )
        severity = data.get("severity", "medium")
        if severity not in ("high", "medium", "low"):
            severity = "medium"
        return Contradiction(
            statement=data.get("statement", ""),
            conflicting_sides=sides,
            severity=severity,
        )
