from __future__ import annotations

import time
import re

from app.core.logging import get_logger
from app.methodology.config import get_methodology_settings
from app.methodology.models import MethodologyProfile, ResearchMethod
from app.rag.llm import RAGLLMProvider
from app.analysis.models import AnalysisResult

logger = get_logger("methodology.method_selector")
settings = get_methodology_settings()

_METHOD_SYSTEM: str = (
    "You are a research methodology selection assistant. "
    "Based on the research analysis, recommend the most suitable research methodologies.\n\n"
    "Available methodologies:\n"
    "- literature_review: Systematic survey of existing literature\n"
    "- systematic_review: Rigorous, reproducible literature review with defined protocols\n"
    "- meta_analysis: Statistical combination of results from multiple studies\n"
    "- comparative_study: Direct comparison of approaches, methods, or systems\n"
    "- experimental_study: Controlled experiments with variables and measurements\n"
    "- survey: Structured data collection from a sample population\n"
    "- case_study: In-depth investigation of a specific instance or phenomenon\n"
    "- benchmark_evaluation: Standardized performance evaluation on benchmarks\n"
    "- ablation_study: Systematic removal of components to measure contribution\n"
    "- hybrid_methodology: Combination of multiple methodologies\n\n"
    "For each recommendation:\n"
    "- Method name\n"
    "- Confidence (0.0-1.0)\n"
    "- Rationale explaining why this method is appropriate\n"
    "- Key requirements\n"
    "- Limitations\n\n"
    "Format:\n"
    "Method: <name>\n"
    "Confidence: 0.X\n"
    "Rationale: <explanation>\n"
    "Requirements: <requirements>\n"
    "Limitations: <limitations>"
)

_METHOD_USER: str = (
    "Research Query: {query}\n"
    "Research Domain: {domain}\n"
    "Evidence Quality: {evidence_quality:.2f}\n"
    "Analysis Summary:\n{analysis_summary}\n\n"
    "Recommend up to {max_methods} research methodologies."
)


class MethodSelector:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def select(
        self,
        query: str,
        analysis_result: AnalysisResult,
    ) -> tuple[list[ResearchMethod], MethodologyProfile]:
        start = time.monotonic()

        profile = self._build_profile(query, analysis_result)
        rule_based = self._rule_based_methods(query, analysis_result)

        llm_methods: list[ResearchMethod] = []
        if self._llm and settings.enable_llm:
            llm_methods = await self._llm_assisted(query, analysis_result, profile)

        seen: set[str] = set()
        merged: list[ResearchMethod] = []
        for m in rule_based + llm_methods:
            key = m.method.lower().strip()
            if key not in seen:
                seen.add(key)
                merged.append(m)

        logger.info(
            "method selection complete",
            extra={
                "rule_based": len(rule_based),
                "llm_assisted": len(llm_methods),
                "merged": len(merged),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return merged[: settings.max_methods], profile

    def _build_profile(self, query: str, ar: AnalysisResult) -> MethodologyProfile:
        domain = "general"
        complexity = "moderate"
        if ar.consensus:
            domain = ar.consensus[0].category
        if hasattr(ar.confidence, "overall"):
            eq = ar.confidence.overall
        else:
            eq = 0.5
        return MethodologyProfile(
            domain=domain,
            complexity=complexity,
            evidence_quality=eq,
            research_goal=query[:200],
        )

    def _rule_based_methods(
        self, query: str, ar: AnalysisResult
    ) -> list[ResearchMethod]:
        methods: list[ResearchMethod] = []
        ql = query.lower()

        if ar.consensus and any(
            c.category in ("comparison", "comparative") for c in ar.consensus
        ) or "compare" in ql or "vs" in ql:
            methods.append(
                ResearchMethod(method="comparative_study", confidence=0.7,
                               rationale="Query involves comparison of approaches",
                               supporting_evidence=[], requirements=["Multiple approaches to compare"],
                               limitations=["Requires controlled conditions"])
            )

        if ar.benchmarks or ar.trends:
            methods.append(
                ResearchMethod(method="benchmark_evaluation", confidence=0.6,
                               rationale="Relevant benchmarks or evaluation trends identified",
                               supporting_evidence=[], requirements=["Standard benchmark datasets"],
                               limitations=["May not cover all aspects"])
            )

        if not methods:
            methods.append(
                ResearchMethod(method="literature_review", confidence=0.5,
                               rationale="General research query suitable for literature review",
                               requirements=["Access to relevant literature"],
                               limitations=["May not provide novel empirical insights"])
            )

        return methods

    async def _llm_assisted(
        self,
        query: str,
        ar: AnalysisResult,
        profile: MethodologyProfile,
    ) -> list[ResearchMethod]:
        try:
            summary = self._summarize_analysis(ar)
            content = await self._llm.generate(
                prompt=_METHOD_USER.format(
                    query=query,
                    domain=profile.domain,
                    evidence_quality=profile.evidence_quality,
                    analysis_summary=summary,
                    max_methods=settings.max_methods,
                ),
                system_prompt=_METHOD_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            return self._parse_methods(content)
        except Exception as exc:
            logger.warning("LLM method selection failed", extra={"error": str(exc)})
            return []

    def _summarize_analysis(self, ar: AnalysisResult) -> str:
        parts = [
            f"Consensus: {len(ar.consensus)} findings",
            f"Contradictions: {len(ar.contradictions)}",
            f"Trends: {len(ar.trends)} identified",
            f"Limitations: {len(ar.limitations)} identified",
            f"Recommendations: {len(ar.recommendations)}",
            f"Confidence: {ar.confidence.overall:.2f}" if hasattr(ar.confidence, "overall") else "",
        ]
        return "\n".join(p for p in parts if p)

    def _parse_methods(self, content: str) -> list[ResearchMethod]:
        results: list[ResearchMethod] = []
        blocks = re.split(r'\n\s*\n', content)
        current: dict = {}
        for block in blocks:
            block = block.strip()
            low = block.lower()
            if low.startswith("method:"):
                if current.get("method"):
                    results.append(self._build_method(current))
                current = {"method": block.split(":", 1)[1].strip()}
            elif low.startswith("confidence:"):
                try:
                    current["confidence"] = float(block.split(":", 1)[1].strip())
                except (ValueError, TypeError):
                    current["confidence"] = 0.5
            elif low.startswith("rationale:"):
                current["rationale"] = block.split(":", 1)[1].strip()
            elif low.startswith("requirements:"):
                current["requirements"] = [r.strip() for r in block.split(":", 1)[1].split(",")]
            elif low.startswith("limitations:"):
                current["limitations"] = [l.strip() for l in block.split(":", 1)[1].split(",")]
        if current.get("method"):
            results.append(self._build_method(current))
        return results

    def _build_method(self, data: dict) -> ResearchMethod:
        return ResearchMethod(
            method=data.get("method", ""),
            confidence=min(1.0, max(0.0, data.get("confidence", 0.5))),
            rationale=data.get("rationale", ""),
            requirements=data.get("requirements", []),
            limitations=data.get("limitations", []),
        )
