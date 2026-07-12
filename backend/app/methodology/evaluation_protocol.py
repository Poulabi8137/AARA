from __future__ import annotations

import time

from app.core.logging import get_logger
from app.methodology.config import get_methodology_settings
from app.methodology.models import EvaluationProtocol
from app.rag.llm import RAGLLMProvider
from app.analysis.models import AnalysisResult

logger = get_logger("methodology.evaluation_protocol")
settings = get_methodology_settings()

_PROTOCOL_SYSTEM: str = (
    "You are an evaluation protocol design assistant. "
    "Based on the research analysis, design a structured evaluation protocol.\n\n"
    "Include:\n"
    "1. Metrics: Specific evaluation metrics appropriate for this research\n"
    "2. Baselines: Strong baseline methods to compare against\n"
    "3. Comparison methods: How different approaches will be compared\n"
    "4. Validation strategy: How results will be validated\n"
    "5. Reproducibility steps: Steps to ensure results can be reproduced\n\n"
    "Format:\n"
    "Metrics: <comma-separated list>\n"
    "Baselines: <comma-separated list>\n"
    "Comparison Methods: <description>\n"
    "Validation Strategy: <description>\n"
    "Reproducibility Steps: <step 1>, <step 2>, ..."
)

_PROTOCOL_USER: str = (
    "Research Query: {query}\n"
    "Recommended Methods: {methods}\n"
    "Analysis Summary:\n{analysis_summary}\n\n"
    "Design an evaluation protocol."
)


class EvaluationProtocolDesigner:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def design(
        self,
        query: str,
        analysis_result: AnalysisResult,
        methods: list[str] | None = None,
    ) -> EvaluationProtocol:
        start = time.monotonic()

        if not self._llm or not settings.enable_llm:
            fallback = EvaluationProtocol(
                metrics=["accuracy", "f1_score", "precision", "recall"],
                baselines=["random_baseline", "majority_class"],
                comparison_methods=["paired_statistical_test"],
                validation_strategy="cross_validation",
                reproducibility_steps=[
                    "seed fixed",
                    "code released",
                    "hyperparameters documented",
                ],
            )
            logger.info("LLM disabled, using default protocol")
            return fallback

        try:
            summary = self._summarize_analysis(analysis_result, methods)
            content = await self._llm.generate(
                prompt=_PROTOCOL_USER.format(
                    query=query,
                    methods=", ".join(methods) if methods else "literature_review",
                    analysis_summary=summary,
                ),
                system_prompt=_PROTOCOL_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            protocol = self._parse_protocol(content)

            logger.info(
                "evaluation protocol designed",
                extra={
                    "metrics": len(protocol.metrics),
                    "baselines": len(protocol.baselines),
                    "reproducibility_steps": len(protocol.reproducibility_steps),
                    "duration_ms": round((time.monotonic() - start) * 1000, 1),
                },
            )
            return protocol
        except Exception as exc:
            logger.warning("LLM protocol design failed", extra={"error": str(exc)})
            return EvaluationProtocol(
                metrics=["accuracy"],
                baselines=["baseline"],
                comparison_methods=["statistical_test"],
                validation_strategy="cross_validation",
                reproducibility_steps=["document setup"],
            )

    def _summarize_analysis(self, ar: AnalysisResult, methods: list[str] | None) -> str:
        parts = [
            f"Consensus: {len(ar.consensus)} findings",
            f"Contradictions: {len(ar.contradictions)}",
            f"Trends: {len(ar.trends)}",
            f"Limitations: {len(ar.limitations)}",
            f"Methods: {', '.join(methods) if methods else 'N/A'}",
        ]
        return "\n".join(parts)

    def _parse_protocol(self, content: str) -> EvaluationProtocol:
        lines = content.split("\n")
        protocol: dict = {
            "metrics": [],
            "baselines": [],
            "comparison_methods": [],
            "validation_strategy": "",
            "reproducibility_steps": [],
        }

        for line in lines:
            line = line.strip()
            if not line:
                continue
            low = line.lower()
            if low.startswith("metrics:"):
                protocol["metrics"] = [
                    m.strip() for m in line.split(":", 1)[1].split(",") if m.strip()
                ]
            elif low.startswith("baselines:"):
                protocol["baselines"] = [
                    b.strip() for b in line.split(":", 1)[1].split(",") if b.strip()
                ]
            elif low.startswith("comparison methods:"):
                protocol["comparison_methods"] = [
                    c.strip() for c in line.split(":", 1)[1].split(",") if c.strip()
                ]
            elif low.startswith("validation strategy:"):
                protocol["validation_strategy"] = line.split(":", 1)[1].strip()
            elif low.startswith("reproducibility steps:"):
                steps = [
                    s.strip() for s in line.split(":", 1)[1].split(",") if s.strip()
                ]
                protocol["reproducibility_steps"] = steps

        return EvaluationProtocol(
            metrics=protocol.get("metrics", []),
            baselines=protocol.get("baselines", []),
            comparison_methods=protocol.get("comparison_methods", []),
            validation_strategy=protocol.get("validation_strategy", ""),
            reproducibility_steps=protocol.get("reproducibility_steps", []),
        )
