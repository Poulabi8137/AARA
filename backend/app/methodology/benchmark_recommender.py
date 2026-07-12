from __future__ import annotations

import re
import time

from app.core.logging import get_logger
from app.methodology.config import get_methodology_settings
from app.methodology.models import BenchmarkRecommendation
from app.rag.llm import RAGLLMProvider
from app.analysis.models import AnalysisResult

logger = get_logger("methodology.benchmark_recommender")
settings = get_methodology_settings()

_BENCHMARK_SYSTEM: str = (
    "You are a benchmark recommendation assistant. "
    "Based on the research analysis, recommend suitable evaluation benchmarks.\n\n"
    "Categories: standard|emerging|domain_specific\n\n"
    "For each benchmark:\n"
    "- Benchmark name\n"
    "- Category (standard|emerging|domain_specific)\n"
    "- Relevance (0.0-1.0)\n"
    "- Rationale explaining why it's appropriate\n"
    "- Confidence (0.0-1.0)\n\n"
    "Format:\n"
    "Benchmark: <name>\n"
    "Category: <category>\n"
    "Relevance: 0.X\n"
    "Rationale: <explanation>\n"
    "Confidence: 0.X"
)

_BENCHMARK_USER: str = (
    "Research Query: {query}\n"
    "Analysis Summary:\n{analysis_summary}\n\n"
    "Recommend up to {max_benchmarks} suitable benchmarks."
)


class BenchmarkRecommender:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def recommend(
        self,
        query: str,
        analysis_result: AnalysisResult,
    ) -> list[BenchmarkRecommendation]:
        start = time.monotonic()

        rule_based = self._rule_based(analysis_result)
        llm_recs: list[BenchmarkRecommendation] = []
        if self._llm and settings.enable_llm:
            llm_recs = await self._llm_assisted(query, analysis_result)

        seen: set[str] = set()
        merged: list[BenchmarkRecommendation] = []
        for r in rule_based + llm_recs:
            key = r.benchmark_name.lower().strip()
            if key and key not in seen:
                seen.add(key)
                merged.append(r)

        logger.info(
            "benchmark recommendation complete",
            extra={
                "rule_based": len(rule_based),
                "llm_assisted": len(llm_recs),
                "merged": len(merged),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return merged[: settings.max_benchmarks]

    def _rule_based(self, ar: AnalysisResult) -> list[BenchmarkRecommendation]:
        benchmarks: list[BenchmarkRecommendation] = []
        seen_names: set[str] = set()

        for section in ar.sections:
            matches = re.findall(
                r"\b([A-Z][A-Za-z0-9-]+(?:Bench|Benchmark|Score|Eval))\b",
                section.content,
            )
            for name in matches:
                if name not in seen_names:
                    seen_names.add(name)
                    benchmarks.append(
                        BenchmarkRecommendation(
                            benchmark_name=name,
                            category="standard",
                            relevance=0.5,
                            rationale="Mentioned in analysis",
                            confidence=0.4,
                        )
                    )

        for trend in ar.trends:
            if (
                "benchmark" in trend.trend.lower()
                or "evaluation" in trend.trend.lower()
            ):
                benchmarks.append(
                    BenchmarkRecommendation(
                        benchmark_name=trend.trend[:60],
                        category="standard",
                        relevance=0.6,
                        rationale="Identified as research trend",
                        confidence=0.5,
                    )
                )

        return benchmarks

    async def _llm_assisted(
        self, query: str, ar: AnalysisResult
    ) -> list[BenchmarkRecommendation]:
        try:
            summary = self._summarize_analysis(ar)
            content = await self._llm.generate(
                prompt=_BENCHMARK_USER.format(
                    query=query,
                    analysis_summary=summary,
                    max_benchmarks=settings.max_benchmarks,
                ),
                system_prompt=_BENCHMARK_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            return self._parse_benchmarks(content)
        except Exception as exc:
            logger.warning(
                "LLM benchmark recommendation failed", extra={"error": str(exc)}
            )
            return []

    def _summarize_analysis(self, ar: AnalysisResult) -> str:
        parts = [
            f"Consensus: {len(ar.consensus)} findings",
            f"Trends: {len(ar.trends)}",
            f"Confidence: {ar.confidence.overall:.2f}"
            if hasattr(ar.confidence, "overall")
            else "",
        ]
        return "\n".join(p for p in parts if p)

    def _parse_benchmarks(self, content: str) -> list[BenchmarkRecommendation]:
        results: list[BenchmarkRecommendation] = []
        blocks = re.split(r"\n\s*\n", content)
        current: dict = {}
        for block in blocks:
            block = block.strip()
            low = block.lower()
            if low.startswith("benchmark:"):
                if current.get("benchmark"):
                    results.append(self._build_benchmark(current))
                current = {"benchmark": block.split(":", 1)[1].strip()}
            elif low.startswith("category:"):
                current["category"] = block.split(":", 1)[1].strip().lower()
            elif low.startswith("relevance:"):
                current["relevance"] = self._parse_float(block)
            elif low.startswith("rationale:"):
                current["rationale"] = block.split(":", 1)[1].strip()
            elif low.startswith("confidence:"):
                current["confidence"] = self._parse_float(block)
        if current.get("benchmark"):
            results.append(self._build_benchmark(current))
        return results

    def _parse_float(self, block: str) -> float:
        try:
            return float(block.split(":", 1)[1].strip())
        except (ValueError, IndexError, TypeError):
            return 0.5

    def _build_benchmark(self, data: dict) -> BenchmarkRecommendation:
        cat = data.get("category", "standard")
        if cat not in ("standard", "emerging", "domain_specific"):
            cat = "standard"
        return BenchmarkRecommendation(
            benchmark_name=data.get("benchmark", ""),
            category=cat,
            relevance=data.get("relevance", 0.5),
            rationale=data.get("rationale", ""),
            confidence=data.get("confidence", 0.5),
        )
