from __future__ import annotations

import time
import re
from collections import defaultdict

from app.core.logging import get_logger
from app.analysis.config import get_analysis_settings
from app.analysis.models import ResearchTrend
from app.rag.llm import RAGLLMProvider
from app.summarization.models import EvidenceGroup

logger = get_logger("analysis.trends")
settings = get_analysis_settings()

_TREND_SYSTEM: str = (
    "You are a research trend analysis assistant. "
    "Analyze the provided evidence groups and identify research trends.\n\n"
    "Consider:\n"
    "1. Emerging topics (new, growing interest)\n"
    "2. Declining topics (less recent activity)\n"
    "3. Stable topics (consistent activity over time)\n"
    "4. Methodology evolution\n"
    "5. Dataset evolution\n\n"
    "Format:\n"
    "Trend: <description>\n"
    "Direction: emerging|declining|stable\n"
    "Sources: [1], [2]\n"
    "Time Range: 2018-2023"
)

_TREND_USER: str = (
    "Research Topic: {query}\n\n"
    "Evidence Groups:\n{groups}\n\n"
    "Identify up to {max} research trends from the evidence."
)


class TrendAnalyzer:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def analyze(
        self,
        query: str,
        groups: list[EvidenceGroup],
    ) -> list[ResearchTrend]:
        start = time.monotonic()
        rule_based = self._rule_based_trends(groups)

        llm_trends: list[ResearchTrend] = []
        if self._llm and settings.enable_llm_analysis:
            llm_trends = await self._llm_assisted(query, groups)

        merged = self._merge_results(rule_based, llm_trends)

        logger.info(
            "trend analysis complete",
            extra={
                "rule_based": len(rule_based),
                "llm_assisted": len(llm_trends),
                "merged": len(merged),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return merged[: settings.max_trends]

    def _rule_based_trends(self, groups: list[EvidenceGroup]) -> list[ResearchTrend]:
        year_buckets: dict[str, int] = defaultdict(int)
        topic_years: dict[str, list[str]] = defaultdict(list)

        for group in groups:
            for ev in group.evidence:
                year = ev.metadata.get("year", "")
                ts = ev.metadata.get("created_at", "")
                if not year and ts:
                    try:
                        year = str(int(ts[:4]))
                    except (ValueError, IndexError):
                        year = ""
                if year:
                    year_buckets[str(year)] += 1
                    topic = group.label
                    topic_years[topic].append(str(year))

        trends: list[ResearchTrend] = []

        for topic, years in topic_years.items():
            if len(years) >= 2:
                int_years = sorted(int(y) for y in years if y.isdigit())
                if len(int_years) >= 2:
                    span = int_years[-1] - int_years[0]
                    direction = "stable"
                    if span <= settings.trend_window_years and int_years[-1] >= 2023:
                        direction = "emerging"
                    elif span > 5 and int_years[-1] >= int_years[0] + 3:
                        direction = "declining"
                    trends.append(
                        ResearchTrend(
                            trend=f"Research activity in {topic}",
                            direction=direction,
                            evidence=[f"[{i}]" for i, _ in enumerate(years)],
                            time_range=(str(int_years[0]), str(int_years[-1])),
                            confidence=0.5,
                        )
                    )

        if not trends and year_buckets:
            years = sorted(year_buckets.keys())
            trends.append(
                ResearchTrend(
                    trend="General research activity in the topic area",
                    direction="stable",
                    time_range=(years[0], years[-1])
                    if len(years) >= 2
                    else (years[0], years[0]),
                    confidence=0.3,
                )
            )

        return trends

    async def _llm_assisted(
        self,
        query: str,
        groups: list[EvidenceGroup],
    ) -> list[ResearchTrend]:
        try:
            groups_text = self._format_groups(groups)
            content = await self._llm.generate(
                prompt=_TREND_USER.format(
                    query=query,
                    groups=groups_text,
                    max=settings.max_trends,
                ),
                system_prompt=_TREND_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            return self._parse_trends(content)
        except Exception as exc:
            logger.warning("LLM trend analysis failed", extra={"error": str(exc)})
            return []

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

    def _parse_trends(self, content: str) -> list[ResearchTrend]:
        results: list[ResearchTrend] = []
        blocks = re.split(r"\n\s*\n", content)
        current: dict = {}
        for block in blocks:
            block = block.strip()
            low = block.lower()
            if low.startswith("trend:"):
                if current.get("trend"):
                    results.append(self._build_trend(current))
                current = {"trend": block.split(":", 1)[1].strip()}
            elif low.startswith("direction:"):
                current["direction"] = block.split(":", 1)[1].strip().lower()
            elif low.startswith("sources:"):
                current["sources"] = re.findall(r"\[\d+\]", block)
            elif low.startswith("time range:"):
                parts = block.split(":", 1)[1].strip().split("-")
                if len(parts) == 2:
                    current["time_range"] = (parts[0].strip(), parts[1].strip())
        if current.get("trend"):
            results.append(self._build_trend(current))
        return results

    def _build_trend(self, data: dict) -> ResearchTrend:
        tr = data.get("time_range", ("", ""))
        if isinstance(tr, list):
            tr = tuple(tr[:2]) if len(tr) >= 2 else ("", "")
        return ResearchTrend(
            trend=data.get("trend", ""),
            direction=data.get("direction", "stable"),
            evidence=data.get("sources", []),
            time_range=tr if isinstance(tr, tuple) else ("", ""),
            confidence=0.5,
        )

    def _merge_results(
        self,
        rule_based: list[ResearchTrend],
        llm_based: list[ResearchTrend],
    ) -> list[ResearchTrend]:
        seen: set[str] = set()
        merged: list[ResearchTrend] = []
        for r in rule_based + llm_based:
            key = r.trend[:80].lower()
            if key not in seen:
                seen.add(key)
                merged.append(r)
        return merged
