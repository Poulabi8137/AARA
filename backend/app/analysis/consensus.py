from __future__ import annotations

import time
import re
from collections import defaultdict

from app.core.logging import get_logger
from app.analysis.config import get_analysis_settings
from app.analysis.models import ConsensusResult
from app.rag.llm import RAGLLMProvider
from app.summarization.models import EvidenceGroup, SummaryResult

logger = get_logger("analysis.consensus")
settings = get_analysis_settings()

_CONSENSUS_SYSTEM: str = (
    "You are a research consensus analysis assistant. "
    "Analyze the provided evidence groups and identify statements where multiple sources agree. "
    "Focus on:\n"
    "1. Widely accepted findings\n"
    "2. Replicated results\n"
    "3. Dominant methodologies\n"
    "4. Strong evidence patterns\n\n"
    "For each consensus point, list the supporting citation keys.\n"
    "Format:\n"
    "Consensus: <statement>\n"
    "Sources: [1], [2], [3]\n"
    "Category: methodology|finding|result|approach"
)

_CONSENSUS_USER: str = (
    "Research Topic: {query}\n\n"
    "Evidence Groups:\n{groups}\n\n"
    "Identify up to {max} areas of consensus across these sources. "
    "For each, list which sources agree and what they agree on."
)


class ConsensusDetector:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def detect(
        self,
        query: str,
        groups: list[EvidenceGroup],
    ) -> list[ConsensusResult]:
        start = time.monotonic()
        rule_based = self._rule_based_consensus(groups)

        llm_consensus: list[ConsensusResult] = []
        if self._llm and settings.enable_llm_analysis:
            llm_consensus = await self._llm_assisted(query, groups)

        merged = self._merge_results(rule_based, llm_consensus)

        logger.info(
            "consensus detection complete",
            extra={
                "rule_based": len(rule_based),
                "llm_assisted": len(llm_consensus),
                "merged": len(merged),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return merged[: settings.max_consensus]

    def _rule_based_consensus(
        self, groups: list[EvidenceGroup]
    ) -> list[ConsensusResult]:
        results: list[ConsensusResult] = []

        for group in groups:
            if len(group.evidence) >= 2:
                sources = group.citation_keys[:]
                results.append(
                    ConsensusResult(
                        statement=f"Multiple sources address the topic: {group.label}",
                        supporting_sources=sources,
                        evidence_count=len(sources),
                        confidence=min(0.9, 0.3 + len(sources) * 0.1),
                        category="topic",
                    )
                )

        if not results:
            all_sources: list[str] = []
            for g in groups:
                all_sources.extend(g.citation_keys)
            if len(set(all_sources)) >= 2:
                results.append(
                    ConsensusResult(
                        statement="Multiple sources found on the research topic",
                        supporting_sources=list(set(all_sources))[:5],
                        evidence_count=len(set(all_sources)),
                        confidence=0.3,
                        category="general",
                    )
                )

        return results

    async def _llm_assisted(
        self,
        query: str,
        groups: list[EvidenceGroup],
    ) -> list[ConsensusResult]:
        try:
            groups_text = self._format_groups(groups)
            content = await self._llm.generate(
                prompt=_CONSENSUS_USER.format(
                    query=query,
                    groups=groups_text,
                    max=settings.max_consensus,
                ),
                system_prompt=_CONSENSUS_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            return self._parse_consensus(content)
        except Exception as exc:
            logger.warning("LLM consensus analysis failed", extra={"error": str(exc)})
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

    def _parse_consensus(self, content: str) -> list[ConsensusResult]:
        results: list[ConsensusResult] = []
        blocks = re.split(r'\n\s*\n', content)
        current: dict = {}
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            if block.lower().startswith("consensus:"):
                if current.get("statement"):
                    results.append(self._build_consensus(current))
                current = {"statement": block.split(":", 1)[1].strip()}
            elif block.lower().startswith("sources:"):
                current["sources"] = re.findall(r'\[\d+\]', block)
            elif block.lower().startswith("category:"):
                current["category"] = block.split(":", 1)[1].strip()
        if current.get("statement"):
            results.append(self._build_consensus(current))
        return results

    def _build_consensus(self, data: dict) -> ConsensusResult:
        sources = data.get("sources", [])
        return ConsensusResult(
            statement=data.get("statement", ""),
            supporting_sources=sources,
            evidence_count=len(sources),
            confidence=min(0.95, 0.3 + len(sources) * 0.1),
            category=data.get("category", "general"),
        )

    def _merge_results(
        self,
        rule_based: list[ConsensusResult],
        llm_based: list[ConsensusResult],
    ) -> list[ConsensusResult]:
        seen: set[str] = set()
        merged: list[ConsensusResult] = []
        for r in rule_based + llm_based:
            key = r.statement[:80].lower()
            if key not in seen:
                seen.add(key)
                merged.append(r)
        merged.sort(key=lambda x: x.confidence, reverse=True)
        return merged
