from __future__ import annotations

import time

from app.core.logging import get_logger
from app.experiments.config import get_experiment_settings
from app.experiments.models import ExperimentPhase, RiskMitigation
from app.methodology.models import MethodologyResult
from app.rag.llm import RAGLLMProvider

logger = get_logger("experiments.risks")
settings = get_experiment_settings()

_RISK_SYSTEM: str = (
    "You are an experiment risk analysis assistant. "
    "Identify technical, experimental, reproducibility, data, and implementation risks.\n\n"
    "Categories: technical | experimental | reproducibility | data | implementation\n\n"
    "For each risk:\n"
    "- Risk description\n"
    "- Category\n"
    "- Severity (high|medium|low)\n"
    "- Likelihood (0.0-1.0)\n"
    "- Impact (high|medium|low)\n"
    "- Mitigation strategy\n"
    "- Fallback plan\n\n"
    "Format:\n"
    "Risk: <description>\n"
    "Category: <category>\n"
    "Severity: high|medium|low\n"
    "Likelihood: 0.X\n"
    "Impact: high|medium|low\n"
    "Mitigation: <strategy>\n"
    "Fallback: <plan>"
)

_RISK_USER: str = (
    "Research Query: {query}\n"
    "Methods: {methods}\n"
    "Number of Phases: {num_phases}\n"
    "Existing Methodology Risks: {existing_risks}\n\n"
    "Identify up to {max_risks} risks for this experiment."
)


class ExperimentRiskAnalyzer:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def analyze(
        self,
        query: str,
        methodology_result: MethodologyResult,
        phases: list[ExperimentPhase],
    ) -> list[RiskMitigation]:
        start = time.monotonic()

        rule_based = self._rule_based(methodology_result, phases)

        llm_risks: list[RiskMitigation] = []
        if self._llm and settings.enable_llm:
            llm_risks = await self._llm_analyze(query, methodology_result, phases)

        seen: set[str] = set()
        merged: list[RiskMitigation] = []
        for r in rule_based + llm_risks:
            key = r.risk[:80].lower()
            if key not in seen:
                seen.add(key)
                merged.append(r)

        merged.sort(key=lambda x: {"high": 3, "medium": 2, "low": 1}.get(x.severity, 0), reverse=True)

        logger.info(
            "risk analysis complete",
            extra={
                "rule_based": len(rule_based),
                "llm_assisted": len(llm_risks),
                "merged": len(merged),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return merged[: settings.max_risks]

    def _rule_based(
        self,
        mr: MethodologyResult,
        phases: list[ExperimentPhase],
    ) -> list[RiskMitigation]:
        risks: list[RiskMitigation] = []

        has_gpu = any(
            p.phase_type in ("training", "evaluation")
            for p in phases
        )
        if has_gpu:
            risks.append(
                RiskMitigation(
                    risk="GPU resource contention or insufficient compute",
                    category="technical",
                    severity="high",
                    likelihood=0.4,
                    impact="high",
                    mitigation="Reserve GPU resources in advance; use cloud spot instances",
                    fallback="Use CPU-only training with reduced model size",
                )
            )

        for p in phases:
            for s in p.steps:
                if s.estimated_minutes > 480:
                    risks.append(
                        RiskMitigation(
                            risk=f"Step '{s.name}' exceeds estimated duration ({s.estimated_minutes} min)",
                            category="experimental",
                            severity="medium",
                            likelihood=0.3,
                            impact="medium",
                            mitigation="Add checkpointing and progress monitoring",
                            fallback="Reduce scope or increase parallelization",
                        )
                    )

        if mr.risks:
            for existing in mr.risks[:3]:
                risks.append(
                    RiskMitigation(
                        risk=f"Methodology risk: {existing.risk[:100]}",
                        category=existing.category,
                        severity=existing.severity,
                        likelihood=existing.confidence,
                        impact=existing.severity,
                        mitigation=existing.mitigation or "Address via experiment design",
                        fallback="Revisit methodology",
                    )
                )

        return risks

    async def _llm_analyze(
        self,
        query: str,
        mr: MethodologyResult,
        phases: list[ExperimentPhase],
    ) -> list[RiskMitigation]:
        try:
            methods_text = ", ".join(m.method for m in mr.methods[:5]) if mr.methods else "none"
            existing_risks = "; ".join(
                f"[{r.severity}] {r.risk[:60]}" for r in mr.risks[:5]
            ) if mr.risks else "none"

            content = await self._llm.generate(
                prompt=_RISK_USER.format(
                    query=query,
                    methods=methods_text,
                    num_phases=len(phases),
                    existing_risks=existing_risks,
                    max_risks=settings.max_risks,
                ),
                system_prompt=_RISK_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            return self._parse_risks(content)
        except Exception as exc:
            logger.warning("LLM risk analysis failed", extra={"error": str(exc)})
            return []

    def _parse_risks(self, content: str) -> list[RiskMitigation]:
        import re
        results: list[RiskMitigation] = []
        blocks = re.split(r'\n\s*\n', content.strip())
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
                current["severity"] = block.split(":", 1)[1].strip().lower()
            elif low.startswith("likelihood:"):
                try:
                    current["likelihood"] = float(block.split(":")[1].strip())
                except (ValueError, TypeError):
                    current["likelihood"] = 0.5
            elif low.startswith("impact:"):
                current["impact"] = block.split(":", 1)[1].strip().lower()
            elif low.startswith("mitigation:"):
                current["mitigation"] = block.split(":", 1)[1].strip()
            elif low.startswith("fallback:"):
                current["fallback"] = block.split(":", 1)[1].strip()
        if current.get("risk"):
            results.append(self._build_risk(current))
        return results

    def _build_risk(self, data: dict) -> RiskMitigation:
        return RiskMitigation(
            risk=data.get("risk", ""),
            category=data.get("category", "technical"),
            severity=data.get("severity", "medium"),
            likelihood=data.get("likelihood", 0.5),
            impact=data.get("impact", "medium"),
            mitigation=data.get("mitigation", ""),
            fallback=data.get("fallback", ""),
        )
