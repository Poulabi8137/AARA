from __future__ import annotations

import time

from app.analysis.models import AnalysisResult
from app.core.logging import get_logger
from app.experiments.config import get_experiment_settings
from app.experiments.models import ExperimentHypothesis, VariableDefinition
from app.methodology.models import MethodologyResult
from app.rag.llm import RAGLLMProvider

logger = get_logger("experiments.variables")
settings = get_experiment_settings()

_VARIABLE_SYSTEM: str = (
    "You are an experiment variable planning assistant. "
    "Define experiment variables for the given research hypotheses.\n\n"
    "Categories: independent | dependent | controlled | confounding\n\n"
    "For each variable:\n"
    "- Name\n"
    "- Type (independent|dependent|controlled|confounding)\n"
    "- Description\n"
    "- Expected effect\n"
    "- Reasoning\n"
    "- Possible values (comma-separated)\n\n"
    "Format:\n"
    "Variable: <name>\n"
    "Type: <independent|dependent|controlled|confounding>\n"
    "Description: <description>\n"
    "Expected Effect: <effect>\n"
    "Reasoning: <rationale>\n"
    "Values: <comma-separated>"
)

_VARIABLE_USER: str = (
    "Research Query: {query}\n"
    "Hypotheses: {hypotheses}\n"
    "Methods: {methods}\n\n"
    "Define experiment variables."
)


class VariablePlanner:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def plan(
        self,
        query: str,
        analysis_result: AnalysisResult,
        methodology_result: MethodologyResult,
        hypotheses: list[ExperimentHypothesis],
    ) -> list[VariableDefinition]:
        start = time.monotonic()

        rule_based = self._rule_based(hypotheses)

        llm_vars: list[VariableDefinition] = []
        if self._llm and settings.enable_llm:
            llm_vars = await self._llm_plan(query, methodology_result, hypotheses)

        seen: set[str] = set()
        merged: list[VariableDefinition] = []
        for v in rule_based + llm_vars:
            key = v.name.lower()
            if key not in seen:
                seen.add(key)
                merged.append(v)

        logger.info(
            "variable planning complete",
            extra={
                "rule_based": len(rule_based),
                "llm_assisted": len(llm_vars),
                "merged": len(merged),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return merged[: settings.max_variables]

    def _rule_based(
        self,
        hypotheses: list[ExperimentHypothesis],
    ) -> list[VariableDefinition]:
        variables: list[VariableDefinition] = []

        for h in hypotheses:
            variables.append(
                VariableDefinition(
                    name=f"treatment_{hypotheses.index(h) + 1}",
                    variable_type="independent",
                    description=f"Application of hypothesis: {h.hypothesis[:80]}",
                    expected_effect="Measured change in dependent variables",
                    reasoning=h.rationale[:100] if h.rationale else "",
                    possible_values=["control", "treatment"],
                )
            )

        variables.append(
            VariableDefinition(
                name="performance_metric",
                variable_type="dependent",
                description="Primary performance measurement",
                expected_effect="Expected improvement over baselines",
                reasoning="Standard evaluation of research hypotheses",
                possible_values=[],
            )
        )

        variables.append(
            VariableDefinition(
                name="random_seed",
                variable_type="controlled",
                description="Random seed for reproducibility",
                expected_effect="Ensures deterministic results",
                reasoning="Controls stochasticity in training and evaluation",
                possible_values=["42", "123", "2024"],
            )
        )

        return variables

    async def _llm_plan(
        self,
        query: str,
        methodology_result: MethodologyResult,
        hypotheses: list[ExperimentHypothesis],
    ) -> list[VariableDefinition]:
        try:
            hypo_text = (
                "; ".join(f"[{h.category}] {h.hypothesis[:80]}" for h in hypotheses[:5])
                if hypotheses
                else "none"
            )
            methods_text = (
                ", ".join(m.method for m in methodology_result.methods[:5])
                if methodology_result.methods
                else "none"
            )

            content = await self._llm.generate(
                prompt=_VARIABLE_USER.format(
                    query=query,
                    hypotheses=hypo_text,
                    methods=methods_text,
                ),
                system_prompt=_VARIABLE_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            return self._parse_variables(content)
        except Exception as exc:
            logger.warning("LLM variable planning failed", extra={"error": str(exc)})
            return []

    def _parse_variables(self, content: str) -> list[VariableDefinition]:
        import re

        results: list[VariableDefinition] = []
        blocks = re.split(r"\n\s*\n", content.strip())
        current: dict = {}
        for block in blocks:
            block = block.strip()
            low = block.lower()
            if low.startswith("variable:"):
                if current.get("name"):
                    results.append(self._build_variable(current))
                current = {"name": block.split(":", 1)[1].strip()}
            elif low.startswith("type:"):
                current["type"] = block.split(":", 1)[1].strip().lower()
            elif low.startswith("description:"):
                current["description"] = block.split(":", 1)[1].strip()
            elif low.startswith("expected effect:"):
                current["effect"] = block.split(":", 1)[1].strip()
            elif low.startswith("reasoning:"):
                current["reasoning"] = block.split(":", 1)[1].strip()
            elif low.startswith("values:"):
                vals = [
                    v.strip() for v in block.split(":", 1)[1].split(",") if v.strip()
                ]
                current["values"] = vals
        if current.get("name"):
            results.append(self._build_variable(current))
        return results

    def _build_variable(self, data: dict) -> VariableDefinition:
        return VariableDefinition(
            name=data.get("name", ""),
            variable_type=data.get("type", "independent"),
            description=data.get("description", ""),
            expected_effect=data.get("effect", ""),
            reasoning=data.get("reasoning", ""),
            possible_values=data.get("values", []),
        )
