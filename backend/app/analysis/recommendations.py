from __future__ import annotations

import time
import re

from app.core.logging import get_logger
from app.analysis.config import get_analysis_settings
from app.analysis.models import Recommendation
from app.rag.llm import RAGLLMProvider
from app.summarization.models import EvidenceGroup

logger = get_logger("analysis.recommendations")
settings = get_analysis_settings()

_RECOMMENDATION_SYSTEM: str = (
    "You are a research recommendation assistant. "
    "Based on the provided evidence, generate actionable recommendations.\n\n"
    "Categories:\n"
    "- experiment: Suggested experiments or analyses\n"
    "- dataset: Useful datasets to explore\n"
    "- methodology: Methodology improvements\n"
    "- reading: Additional papers or topics to read\n"
    "- benchmark: Benchmark suggestions\n"
    "- future_work: Future research directions\n\n"
    "Format:\n"
    "Recommendation: <description>\n"
    "Category: <category>\n"
    "Sources: [1], [2]\n"
    "Priority: 1-10"
)

_RECOMMENDATION_USER: str = (
    "Research Topic: {query}\n\n"
    "Evidence Groups:\n{groups}\n\n"
    "Generate up to {max} recommendations based on the evidence."
)


class RecommendationEngine:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def generate(
        self,
        query: str,
        groups: list[EvidenceGroup],
    ) -> list[Recommendation]:
        start = time.monotonic()

        rule_based = self._rule_based_recommendations(groups)

        llm_recs: list[Recommendation] = []
        if self._llm and settings.enable_llm_analysis:
            llm_recs = await self._llm_assisted(query, groups)

        seen: set[str] = set()
        merged: list[Recommendation] = []
        for r in rule_based + llm_recs:
            key = r.recommendation[:80].lower()
            if key not in seen:
                seen.add(key)
                merged.append(r)

        merged.sort(key=lambda x: x.priority, reverse=True)

        logger.info(
            "recommendation generation complete",
            extra={
                "rule_based": len(rule_based),
                "llm_assisted": len(llm_recs),
                "merged": len(merged),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return merged[: settings.max_recommendations]

    def _rule_based_recommendations(
        self, groups: list[EvidenceGroup]
    ) -> list[Recommendation]:
        recs: list[Recommendation] = []
        for group in groups:
            if "dataset" in group.label.lower() or "data" in group.label.lower():
                recs.append(
                    Recommendation(
                        recommendation=f"Explore datasets identified in the {group.label} group",
                        category="dataset",
                        supporting_evidence=group.citation_keys[:3],
                        confidence=0.6,
                        priority=6,
                    )
                )
            if "method" in group.label.lower() or "approach" in group.label.lower():
                recs.append(
                    Recommendation(
                        recommendation=f"Consider the methodologies discussed in {group.label}",
                        category="methodology",
                        supporting_evidence=group.citation_keys[:3],
                        confidence=0.6,
                        priority=7,
                    )
                )
        return recs

    async def _llm_assisted(
        self,
        query: str,
        groups: list[EvidenceGroup],
    ) -> list[Recommendation]:
        try:
            groups_text = self._format_groups(groups)
            content = await self._llm.generate(
                prompt=_RECOMMENDATION_USER.format(
                    query=query,
                    groups=groups_text,
                    max=settings.max_recommendations,
                ),
                system_prompt=_RECOMMENDATION_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            return self._parse_recommendations(content)
        except Exception as exc:
            logger.warning("LLM recommendation failed", extra={"error": str(exc)})
            return []

    def _format_groups(self, groups: list[EvidenceGroup]) -> str:
        parts: list[str] = []
        for i, group in enumerate(groups, 1):
            header = f"Group {i}: {group.label}"
            texts: list[str] = []
            for j, ev in enumerate(group.evidence):
                key = group.citation_keys[j] if j < len(group.citation_keys) else f"[{j + 1}]"
                texts.append(f"{key} {ev.content[:400]}")
            parts.append(f"{header}\n" + "\n".join(texts))
        return "\n\n".join(parts)

    def _parse_recommendations(self, content: str) -> list[Recommendation]:
        results: list[Recommendation] = []
        blocks = re.split(r'\n\s*\n', content)
        current: dict = {}
        for block in blocks:
            block = block.strip()
            low = block.lower()
            if low.startswith("recommendation:"):
                if current.get("recommendation"):
                    results.append(self._build_recommendation(current))
                current = {"recommendation": block.split(":", 1)[1].strip()}
            elif low.startswith("category:"):
                current["category"] = block.split(":", 1)[1].strip().lower()
            elif low.startswith("sources:"):
                current["sources"] = re.findall(r'\[\d+\]', block)
            elif low.startswith("priority:"):
                try:
                    current["priority"] = int(block.split(":", 1)[1].strip())
                except (ValueError, IndexError):
                    current["priority"] = 5
        if current.get("recommendation"):
            results.append(self._build_recommendation(current))
        return results

    def _build_recommendation(self, data: dict) -> Recommendation:
        return Recommendation(
            recommendation=data.get("recommendation", ""),
            category=data.get("category", "general"),
            supporting_evidence=data.get("sources", []),
            confidence=0.5,
            priority=data.get("priority", 5),
        )
