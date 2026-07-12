from __future__ import annotations

import time
import re

from app.core.logging import get_logger
from app.analysis.config import get_analysis_settings
from app.analysis.models import Limitation
from app.rag.llm import RAGLLMProvider
from app.summarization.models import EvidenceGroup

logger = get_logger("analysis.limitations")
settings = get_analysis_settings()

_LIMITATION_SYSTEM: str = (
    "You are a research limitation analysis assistant. "
    "Analyze the provided evidence and identify limitations.\n\n"
    "Consider:\n"
    "1. Stated limitations (explicitly mentioned by authors)\n"
    "2. Methodological weaknesses\n"
    "3. Missing experiments or validation\n"
    "4. Data limitations (size, quality, bias)\n"
    "5. Scope limitations\n\n"
    "Categories: methodology|data|validation|scope\n"
    "Severity: high|medium|low\n\n"
    "Format:\n"
    "Limitation: <description>\n"
    "Category: <category>\n"
    "Sources: [1], [2]\n"
    "Severity: high|medium|low"
)

_LIMITATION_USER: str = (
    "Research Topic: {query}\n\n"
    "Evidence Groups:\n{groups}\n\n"
    "Identify up to {max} limitations from the evidence."
)


class LimitationAnalyzer:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def analyze(
        self,
        query: str,
        groups: list[EvidenceGroup],
    ) -> list[Limitation]:
        start = time.monotonic()

        rule_based = self._rule_based_limitations(groups)

        llm_limitations: list[Limitation] = []
        if self._llm and settings.enable_llm_analysis:
            llm_limitations = await self._llm_assisted(query, groups)

        seen: set[str] = set()
        merged: list[Limitation] = []
        for r in rule_based + llm_limitations:
            key = r.limitation[:80].lower()
            if key not in seen:
                seen.add(key)
                merged.append(r)

        logger.info(
            "limitation analysis complete",
            extra={
                "rule_based": len(rule_based),
                "llm_assisted": len(llm_limitations),
                "merged": len(merged),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return merged[: settings.max_limitations]

    def _rule_based_limitations(
        self, groups: list[EvidenceGroup]
    ) -> list[Limitation]:
        limitations: list[Limitation] = []
        keywords = [
            "limitation", "weakness", "drawback", "shortcoming", "limitation",
            "not considered", "not evaluated", "future work", "TODO",
        ]

        for group in groups:
            for ev in group.evidence:
                content_lower = ev.content.lower()
                for kw in keywords:
                    if kw in content_lower:
                        sent = self._extract_sentence(ev.content, kw)
                        if sent:
                            limitations.append(
                                Limitation(
                                    limitation=sent,
                                    category=self._categorize(kw),
                                    sources=[ev.source_id],
                                    severity="medium",
                                )
                            )
                        break

        return limitations

    async def _llm_assisted(
        self,
        query: str,
        groups: list[EvidenceGroup],
    ) -> list[Limitation]:
        try:
            groups_text = self._format_groups(groups)
            content = await self._llm.generate(
                prompt=_LIMITATION_USER.format(
                    query=query,
                    groups=groups_text,
                    max=settings.max_limitations,
                ),
                system_prompt=_LIMITATION_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            return self._parse_limitations(content)
        except Exception as exc:
            logger.warning("LLM limitation analysis failed", extra={"error": str(exc)})
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

    def _parse_limitations(self, content: str) -> list[Limitation]:
        results: list[Limitation] = []
        blocks = re.split(r'\n\s*\n', content)
        current: dict = {}
        for block in blocks:
            block = block.strip()
            low = block.lower()
            if low.startswith("limitation:"):
                if current.get("limitation"):
                    results.append(self._build_limitation(current))
                current = {"limitation": block.split(":", 1)[1].strip()}
            elif low.startswith("category:"):
                current["category"] = block.split(":", 1)[1].strip().lower()
            elif low.startswith("sources:"):
                current["sources"] = re.findall(r'\[\d+\]', block)
            elif low.startswith("severity:"):
                current["severity"] = block.split(":", 1)[1].strip().lower()
        if current.get("limitation"):
            results.append(self._build_limitation(current))
        return results

    def _build_limitation(self, data: dict) -> Limitation:
        sev = data.get("severity", "medium")
        if sev not in ("high", "medium", "low"):
            sev = "medium"
        return Limitation(
            limitation=data.get("limitation", ""),
            category=data.get("category", "general"),
            sources=data.get("sources", []),
            severity=sev,
        )

    def _extract_sentence(self, text: str, keyword: str) -> str:
        sentences = re.split(r'[.!?\n]', text)
        for sent in sentences:
            if keyword in sent.lower():
                return sent.strip()[:200]
        return ""

    def _categorize(self, keyword: str) -> str:
        if keyword in ("limitation", "drawback", "shortcoming"):
            return "scope"
        if keyword in ("not considered", "not evaluated", "future work"):
            return "validation"
        return "general"
