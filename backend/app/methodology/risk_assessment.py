from __future__ import annotations

import re
import time

from app.core.logging import get_logger
from app.methodology.config import get_methodology_settings
from app.methodology.models import RiskAssessment
from app.rag.llm import RAGLLMProvider
from app.analysis.models import AnalysisResult

logger = get_logger("methodology.risk_assessment")
settings = get_methodology_settings()

_RISK_CATEGORIES = [
    "dataset_bias",
    "insufficient_evidence",
    "overfitting",
    "reproducibility",
    "evaluation_weakness",
    "ethical_concern",
]

_RISK_SYSTEM: str = (
    "You are a research risk assessment assistant. "
    "Identify methodological risks based on the research analysis.\n\n"
    "Risk categories: dataset_bias|insufficient_evidence|overfitting|reproducibility|evaluation_weakness|ethical_concern\n\n"
    "For each risk:\n"
    "- Risk description\n"
    "- Category (from list above)\n"
    "- Severity (high|medium|low)\n"
    "- Mitigation strategy\n"
    "- Confidence (0.0-1.0)\n\n"
    "Format:\n"
    "Risk: <description>\n"
    "Category: <category>\n"
    "Severity: high|medium|low\n"
    "Mitigation: <strategy>\n"
    "Confidence: 0.X"
)

_RISK_USER: str = (
    "Research Query: {query}\n"
    "Analysis Summary:\n{analysis_summary}\n\n"
    "Identify up to {max_risks} methodological risks."
)


class RiskAssessor:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def assess(
        self,
        query: str,
        analysis_result: AnalysisResult,
    ) -> list[RiskAssessment]:
        start = time.monotonic()

        rule_based = self._rule_based(analysis_result)

        llm_risks: list[RiskAssessment] = []
        if self._llm and settings.enable_llm:
            llm_risks = await self._llm_assisted(query, analysis_result)

        seen: set[str] = set()
        merged: list[RiskAssessment] = []
        for r in rule_based + llm_risks:
            key = r.risk[:80].lower()
            if key not in seen:
                seen.add(key)
                merged.append(r)

        merged.sort(
            key=lambda x: {"high": 3, "medium": 2, "low": 1}.get(x.severity, 0),
            reverse=True,
        )

        logger.info(
            "risk assessment complete",
            extra={
                "rule_based": len(rule_based),
                "llm_assisted": len(llm_risks),
                "merged": len(merged),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return merged[: settings.max_risks]

    def _rule_based(self, ar: AnalysisResult) -> list[RiskAssessment]:
        risks: list[RiskAssessment] = []

        for limitation in ar.limitations:
            cat = "evaluation_weakness"
            if "data" in limitation.category:
                cat = "dataset_bias"
            elif "validation" in limitation.category:
                cat = "reproducibility"
            risks.append(
                RiskAssessment(
                    risk=limitation.limitation[:200],
                    category=cat,
                    severity=limitation.severity,
                    mitigation=f"Address the identified limitation: {limitation.limitation[:100]}",
                    confidence=0.6,
                )
            )

        if ar.confidence.overall < settings.confidence_threshold:
            risks.append(
                RiskAssessment(
                    risk="Low overall confidence in the analysis results",
                    category="insufficient_evidence",
                    severity="high",
                    mitigation="Gather more evidence and improve evidence quality",
                    confidence=0.8,
                )
            )

        if len(ar.contradictions) > 3:
            risks.append(
                RiskAssessment(
                    risk=f"Multiple ({len(ar.contradictions)}) contradictions detected in the evidence",
                    category="insufficient_evidence",
                    severity="high",
                    mitigation="Reconcile conflicting findings through deeper analysis",
                    confidence=0.7,
                )
            )

        return risks

    async def _llm_assisted(
        self, query: str, ar: AnalysisResult
    ) -> list[RiskAssessment]:
        try:
            summary = self._summarize_analysis(ar)
            content = await self._llm.generate(
                prompt=_RISK_USER.format(
                    query=query,
                    analysis_summary=summary,
                    max_risks=settings.max_risks,
                ),
                system_prompt=_RISK_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            return self._parse_risks(content)
        except Exception as exc:
            logger.warning("LLM risk assessment failed", extra={"error": str(exc)})
            return []

    def _summarize_analysis(self, ar: AnalysisResult) -> str:
        parts = [
            f"Consensus: {len(ar.consensus)}",
            f"Contradictions: {len(ar.contradictions)}",
            f"Limitations: {len(ar.limitations)}",
            f"Recommendations: {len(ar.recommendations)}",
            f"Confidence: {ar.confidence.overall:.2f}"
            if hasattr(ar.confidence, "overall")
            else "",
        ]
        return "\n".join(p for p in parts if p)

    def _parse_risks(self, content: str) -> list[RiskAssessment]:
        results: list[RiskAssessment] = []
        blocks = re.split(r"\n\s*\n", content)
        current: dict = {}
        for block in blocks:
            block = block.strip()
            low = block.lower()
            if low.startswith("risk:"):
                if current.get("risk"):
                    results.append(self._build_risk(current))
                current = {"risk": block.split(":", 1)[1].strip()}
            elif low.startswith("category:"):
                current["category"] = block.split(":", 1)[1].strip().lower()
            elif low.startswith("severity:"):
                sev = block.split(":", 1)[1].strip().lower()
                current["severity"] = (
                    sev if sev in ("high", "medium", "low") else "medium"
                )
            elif low.startswith("mitigation:"):
                current["mitigation"] = block.split(":", 1)[1].strip()
            elif low.startswith("confidence:"):
                try:
                    current["confidence"] = float(block.split(":", 1)[1].strip())
                except (ValueError, TypeError):
                    current["confidence"] = 0.5
        if current.get("risk"):
            results.append(self._build_risk(current))
        return results

    def _build_risk(self, data: dict) -> RiskAssessment:
        return RiskAssessment(
            risk=data.get("risk", ""),
            category=data.get("category", "general"),
            severity=data.get("severity", "medium"),
            mitigation=data.get("mitigation", ""),
            confidence=data.get("confidence", 0.5),
        )
