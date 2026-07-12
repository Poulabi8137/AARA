from __future__ import annotations

import re
import time

from app.core.logging import get_logger
from app.methodology.config import get_methodology_settings
from app.methodology.models import ValidationStrategy
from app.rag.llm import RAGLLMProvider
from app.analysis.models import AnalysisResult

logger = get_logger("methodology.validation_strategy")
settings = get_methodology_settings()

_VALIDATION_SYSTEM: str = (
    "You are a validation strategy design assistant. "
    "Based on the research analysis, recommend validation strategies.\n\n"
    "Available strategies:\n"
    "- cross_validation: K-fold or stratified cross-validation\n"
    "- statistical_testing: Hypothesis tests, confidence intervals\n"
    "- replication: Independent replication of results\n"
    "- robustness_testing: Sensitivity to hyperparameters, noise\n"
    "- sensitivity_analysis: Effect of input variations on outputs\n\n"
    "For each strategy:\n"
    "- Strategy name\n"
    "- Description\n"
    "- Strengths\n"
    "- Weaknesses\n"
    "- Confidence (0.0-1.0)\n\n"
    "Format:\n"
    "Strategy: <name>\n"
    "Description: <description>\n"
    "Strengths: <comma-separated>\n"
    "Weaknesses: <comma-separated>\n"
    "Confidence: 0.X"
)

_VALIDATION_USER: str = (
    "Research Query: {query}\n"
    "Analysis Summary:\n{analysis_summary}\n\n"
    "Recommend validation strategies."
)


class ValidationStrategyDesigner:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def design(
        self,
        query: str,
        analysis_result: AnalysisResult,
    ) -> list[ValidationStrategy]:
        start = time.monotonic()

        if not self._llm or not settings.enable_llm:
            defaults = [
                ValidationStrategy(
                    strategy="cross_validation",
                    confidence=0.7,
                    description="K-fold cross-validation to ensure generalization",
                    strengths=["reduces overfitting", "uses all data"],
                    weaknesses=["computationally expensive"],
                ),
                ValidationStrategy(
                    strategy="statistical_testing",
                    confidence=0.6,
                    description="Statistical tests to validate significance",
                    strengths=["rigorous", "quantifiable"],
                    weaknesses=["requires assumptions"],
                ),
            ]
            logger.info("LLM disabled, using default validation strategies")
            return defaults

        try:
            summary = self._summarize_analysis(analysis_result)
            content = await self._llm.generate(
                prompt=_VALIDATION_USER.format(
                    query=query,
                    analysis_summary=summary,
                ),
                system_prompt=_VALIDATION_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            strategies = self._parse_strategies(content)

            logger.info(
                "validation strategy design complete",
                extra={
                    "strategies": len(strategies),
                    "duration_ms": round((time.monotonic() - start) * 1000, 1),
                },
            )
            return strategies
        except Exception as exc:
            logger.warning("LLM validation strategy failed", extra={"error": str(exc)})
            return []

    def _summarize_analysis(self, ar: AnalysisResult) -> str:
        parts = [
            f"Consensus: {len(ar.consensus)} findings",
            f"Contradictions: {len(ar.contradictions)}",
            f"Confidence: {ar.confidence.overall:.2f}"
            if hasattr(ar.confidence, "overall")
            else "",
        ]
        return "\n".join(p for p in parts if p)

    def _parse_strategies(self, content: str) -> list[ValidationStrategy]:
        results: list[ValidationStrategy] = []
        blocks = re.split(r"\n\s*\n", content)
        current: dict = {}
        for block in blocks:
            block = block.strip()
            low = block.lower()
            if low.startswith("strategy:"):
                if current.get("strategy"):
                    results.append(self._build_strategy(current))
                current = {"strategy": block.split(":", 1)[1].strip()}
            elif low.startswith("description:"):
                current["description"] = block.split(":", 1)[1].strip()
            elif low.startswith("strengths:"):
                current["strengths"] = [
                    s.strip() for s in block.split(":", 1)[1].split(",") if s.strip()
                ]
            elif low.startswith("weaknesses:"):
                current["weaknesses"] = [
                    w.strip() for w in block.split(":", 1)[1].split(",") if w.strip()
                ]
            elif low.startswith("confidence:"):
                try:
                    current["confidence"] = float(block.split(":", 1)[1].strip())
                except (ValueError, TypeError):
                    current["confidence"] = 0.5
        if current.get("strategy"):
            results.append(self._build_strategy(current))
        return results

    def _build_strategy(self, data: dict) -> ValidationStrategy:
        return ValidationStrategy(
            strategy=data.get("strategy", ""),
            description=data.get("description", ""),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            confidence=data.get("confidence", 0.5),
        )
