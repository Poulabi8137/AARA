from __future__ import annotations

import time

from app.analysis.models import AnalysisResult
from app.core.logging import get_logger
from app.experiments.config import get_experiment_settings
from app.experiments.models import ExperimentHypothesis
from app.methodology.models import MethodologyResult
from app.rag.llm import RAGLLMProvider

logger = get_logger("experiments.hypothesis")
settings = get_experiment_settings()

_HYPOTHESIS_SYSTEM: str = (
    "You are a research hypothesis generation assistant. "
    "Based on the research analysis and methodology, generate clear, testable research hypotheses.\n\n"
    "Each hypothesis should include:\n"
    "- A clear, falsifiable statement\n"
    "- Rationale explaining why this hypothesis is plausible\n"
    "- Supporting evidence citations from the analysis\n"
    "- Confidence score (0.0-1.0)\n"
    "- Validation criteria describing how to test it\n"
    "- Category: primary | secondary | exploratory\n\n"
    "Format:\n"
    "Hypothesis: <statement>\n"
    "Rationale: <explanation>\n"
    "Evidence: <comma-separated evidence>\n"
    "Confidence: 0.X\n"
    "Validation Criteria: <test description>\n"
    "Category: primary|secondary|exploratory"
)

_HYPOTHESIS_USER: str = (
    "Research Query: {query}\n"
    "Analysis Consensus: {consensus}\n"
    "Analysis Trends: {trends}\n"
    "Analysis Recommendations: {recommendations}\n"
    "Recommended Methods: {methods}\n"
    "Recommended Datasets: {datasets}\n\n"
    "Generate up to {max_hypotheses} research hypotheses."
)


class HypothesisGenerator:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def generate(
        self,
        query: str,
        analysis_result: AnalysisResult,
        methodology_result: MethodologyResult,
    ) -> list[ExperimentHypothesis]:
        start = time.monotonic()

        rule_based = self._rule_based(analysis_result, methodology_result)

        llm_hypotheses: list[ExperimentHypothesis] = []
        if self._llm and settings.enable_llm:
            llm_hypotheses = await self._llm_assisted(
                query, analysis_result, methodology_result
            )

        seen: set[str] = set()
        merged: list[ExperimentHypothesis] = []
        for h in rule_based + llm_hypotheses:
            key = h.hypothesis[:80].lower()
            if key not in seen:
                seen.add(key)
                merged.append(h)

        logger.info(
            "hypotheses generated",
            extra={
                "rule_based": len(rule_based),
                "llm_assisted": len(llm_hypotheses),
                "merged": len(merged),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return merged[: settings.max_hypotheses]

    def _rule_based(
        self,
        analysis_result: AnalysisResult,
        methodology_result: MethodologyResult,
    ) -> list[ExperimentHypothesis]:
        hypotheses: list[ExperimentHypothesis] = []

        for rec in analysis_result.recommendations:
            hn = rec.recommendation[:120]
            hypotheses.append(
                ExperimentHypothesis(
                    hypothesis=hn,
                    rationale=f"Derived from analysis recommendation: {rec.recommendation[:80]}",
                    supporting_evidence=rec.supporting_evidence,
                    confidence=rec.confidence,
                    validation_criteria=f"Evaluate whether {hn.lower()} holds under controlled conditions",
                    category="secondary",
                )
            )

        for trend in analysis_result.trends:
            if trend.confidence > settings.hypothesis_confidence_threshold:
                hypotheses.append(
                    ExperimentHypothesis(
                        hypothesis=f"The trend '{trend.trend}' will continue in the near term",
                        rationale=f"Based on identified research trend with confidence {trend.confidence:.2f}",
                        supporting_evidence=trend.evidence,
                        confidence=trend.confidence,
                        validation_criteria=f"Monitor and measure the direction of '{trend.trend}' over time",
                        category="exploratory",
                    )
                )

        return hypotheses[: settings.max_hypotheses]

    async def _llm_assisted(
        self,
        query: str,
        analysis_result: AnalysisResult,
        methodology_result: MethodologyResult,
    ) -> list[ExperimentHypothesis]:
        try:
            consensus_text = (
                "; ".join(c.statement[:100] for c in analysis_result.consensus[:5])
                if analysis_result.consensus
                else "none"
            )
            trends_text = (
                "; ".join(t.trend[:100] for t in analysis_result.trends[:5])
                if analysis_result.trends
                else "none"
            )
            rec_text = (
                "; ".join(
                    r.recommendation[:100] for r in analysis_result.recommendations[:5]
                )
                if analysis_result.recommendations
                else "none"
            )
            methods_text = (
                ", ".join(m.method for m in methodology_result.methods[:5])
                if methodology_result.methods
                else "none"
            )
            datasets_text = (
                ", ".join(d.dataset_name for d in methodology_result.datasets[:5])
                if methodology_result.datasets
                else "none"
            )

            content = await self._llm.generate(
                prompt=_HYPOTHESIS_USER.format(
                    query=query,
                    consensus=consensus_text,
                    trends=trends_text,
                    recommendations=rec_text,
                    methods=methods_text,
                    datasets=datasets_text,
                    max_hypotheses=settings.max_hypotheses,
                ),
                system_prompt=_HYPOTHESIS_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            return self._parse_hypotheses(content)
        except Exception as exc:
            logger.warning(
                "LLM hypothesis generation failed", extra={"error": str(exc)}
            )
            return []

    def _parse_hypotheses(self, content: str) -> list[ExperimentHypothesis]:
        import re

        results: list[ExperimentHypothesis] = []
        blocks = re.split(r"\n\s*\n", content.strip())
        current: dict = {}
        for block in blocks:
            block = block.strip()
            low = block.lower()
            if low.startswith("hypothesis:"):
                if current.get("hypothesis"):
                    results.append(self._build_hypothesis(current))
                current = {"hypothesis": block.split(":", 1)[1].strip()}
            elif low.startswith("rationale:"):
                current["rationale"] = block.split(":", 1)[1].strip()
            elif low.startswith("evidence:"):
                current["evidence"] = [
                    e.strip() for e in block.split(":", 1)[1].split(",") if e.strip()
                ]
            elif low.startswith("confidence:"):
                try:
                    current["confidence"] = float(block.split(":", 1)[1].strip())
                except (ValueError, TypeError):
                    current["confidence"] = 0.5
            elif low.startswith("validation criteria:"):
                current["validation_criteria"] = block.split(":", 1)[1].strip()
            elif low.startswith("category:"):
                current["category"] = block.split(":", 1)[1].strip().lower()
        if current.get("hypothesis"):
            results.append(self._build_hypothesis(current))
        return results

    def _build_hypothesis(self, data: dict) -> ExperimentHypothesis:
        return ExperimentHypothesis(
            hypothesis=data.get("hypothesis", ""),
            rationale=data.get("rationale", ""),
            supporting_evidence=data.get("evidence", []),
            confidence=data.get("confidence", 0.5),
            validation_criteria=data.get("validation_criteria", ""),
            category=data.get("category", "secondary"),
        )
