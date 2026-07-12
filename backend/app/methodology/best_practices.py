from __future__ import annotations

import re
import time

from app.core.logging import get_logger
from app.methodology.config import get_methodology_settings
from app.methodology.models import BestPractice
from app.rag.llm import RAGLLMProvider
from app.analysis.models import AnalysisResult

logger = get_logger("methodology.best_practices")
settings = get_methodology_settings()

_PRACTICE_SYSTEM: str = (
    "You are a research best practices assistant. "
    "Based on the research analysis, recommend research best practices.\n\n"
    "Categories: reproducibility|documentation|evaluation|ethics|methodology|data_management\n\n"
    "For each practice:\n"
    "- Practice description\n"
    "- Category\n"
    "- Rationale explaining why this practice matters\n"
    "- Source (where this practice comes from)\n\n"
    "Format:\n"
    "Practice: <description>\n"
    "Category: <category>\n"
    "Rationale: <explanation>\n"
    "Source: <reference>"
)

_PRACTICE_USER: str = (
    "Research Query: {query}\n"
    "Domain: {domain}\n"
    "Analysis Summary:\n{analysis_summary}\n\n"
    "Recommend up to {max_practices} research best practices."
)


class BestPracticesEngine:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def generate(
        self,
        query: str,
        analysis_result: AnalysisResult,
    ) -> list[BestPractice]:
        start = time.monotonic()

        rule_based = self._rule_based(analysis_result)

        llm_practices: list[BestPractice] = []
        if self._llm and settings.enable_llm:
            llm_practices = await self._llm_assisted(query, analysis_result)

        seen: set[str] = set()
        merged: list[BestPractice] = []
        for p in rule_based + llm_practices:
            key = p.practice[:80].lower()
            if key not in seen:
                seen.add(key)
                merged.append(p)

        logger.info(
            "best practices generation complete",
            extra={
                "rule_based": len(rule_based),
                "llm_assisted": len(llm_practices),
                "merged": len(merged),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return merged[: settings.max_practices]

    def _rule_based(self, ar: AnalysisResult) -> list[BestPractice]:
        practices: list[BestPractice] = []

        practices.append(
            BestPractice(practice="Report all hyperparameters and configuration details",
                         category="reproducibility",
                         rationale="Essential for result reproducibility",
                         source="ML Reproducibility Checklist")
        )

        if ar.limitations:
            practices.append(
                BestPractice(practice=f"Address identified limitations: {ar.limitations[0].limitation[:80]}",
                             category="methodology",
                             rationale="Limitations should be acknowledged and addressed",
                             source="Research Methodology Standards")
            )

        if ar.confidence.overall < 0.5:
            practices.append(
                BestPractice(practice="Improve evidence quality before drawing strong conclusions",
                             category="evaluation",
                             rationale="Low confidence requires more rigorous validation",
                             source="Evidence-Based Research Principles")
            )

        return practices

    async def _llm_assisted(
        self, query: str, ar: AnalysisResult
    ) -> list[BestPractice]:
        try:
            domain = self._extract_domain(ar)
            summary = self._summarize_analysis(ar)
            content = await self._llm.generate(
                prompt=_PRACTICE_USER.format(
                    query=query,
                    domain=domain,
                    analysis_summary=summary,
                    max_practices=settings.max_practices,
                ),
                system_prompt=_PRACTICE_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            return self._parse_practices(content)
        except Exception as exc:
            logger.warning("LLM best practices failed", extra={"error": str(exc)})
            return []

    def _extract_domain(self, ar: AnalysisResult) -> str:
        if ar.consensus:
            return ar.consensus[0].category
        return "general"

    def _summarize_analysis(self, ar: AnalysisResult) -> str:
        parts = [
            f"Consensus: {len(ar.consensus)}",
            f"Contradictions: {len(ar.contradictions)}",
            f"Limitations: {len(ar.limitations)}",
            f"Confidence: {ar.confidence.overall:.2f}" if hasattr(ar.confidence, "overall") else "",
        ]
        return "\n".join(p for p in parts if p)

    def _parse_practices(self, content: str) -> list[BestPractice]:
        results: list[BestPractice] = []
        blocks = re.split(r'\n\s*\n', content)
        current: dict = {}
        for block in blocks:
            block = block.strip()
            low = block.lower()
            if low.startswith("practice:"):
                if current.get("practice"):
                    results.append(self._build_practice(current))
                current = {"practice": block.split(":", 1)[1].strip()}
            elif low.startswith("category:"):
                current["category"] = block.split(":", 1)[1].strip().lower()
            elif low.startswith("rationale:"):
                current["rationale"] = block.split(":", 1)[1].strip()
            elif low.startswith("source:"):
                current["source"] = block.split(":", 1)[1].strip()
        if current.get("practice"):
            results.append(self._build_practice(current))
        return results

    def _build_practice(self, data: dict) -> BestPractice:
        return BestPractice(
            practice=data.get("practice", ""),
            category=data.get("category", "general"),
            rationale=data.get("rationale", ""),
            source=data.get("source", ""),
        )
