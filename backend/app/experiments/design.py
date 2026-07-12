from __future__ import annotations

import time
from typing import Any

from app.analysis.models import AnalysisResult
from app.core.logging import get_logger
from app.experiments.config import get_experiment_settings
from app.experiments.models import (
    DatasetUsage,
    ExecutionStep,
    ExperimentHypothesis,
    ExperimentObjective,
    ExperimentPhase,
)
from app.methodology.models import MethodologyResult
from app.rag.llm import RAGLLMProvider

logger = get_logger("experiments.design")
settings = get_experiment_settings()

_DESIGN_SYSTEM: str = (
    "You are an experiment design assistant. "
    "Generate structured experiment plans based on research hypotheses and methodology.\n\n"
    "Include phases covering:\n"
    "1. Data preparation (dataset selection, preprocessing, splitting)\n"
    "2. Model/algorithm implementation\n"
    "3. Training and validation\n"
    "4. Evaluation and testing\n"
    "5. Ablation and sensitivity analysis\n"
    "6. Results reporting\n\n"
    "For each phase provide name, description, and execution steps.\n"
    "Each step should have: step_id, name, description, type, estimated_minutes.\n"
    "Format per phase:\n"
    "Phase: <name>\n"
    "Description: <description>\n"
    "Type: preparation|implementation|training|evaluation|analysis|reporting\n"
    "Steps:\n"
    "Step: <step_id> | <name> | <description> | <type> | <minutes>"
)

_DESIGN_USER: str = (
    "Research Query: {query}\n"
    "Hypotheses: {hypotheses}\n"
    "Methods: {methods}\n"
    "Datasets: {datasets}\n"
    "Domain: {domain}\n\n"
    "Design up to {max_phases} experiment phases."
)


class ExperimentDesigner:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def design(
        self,
        query: str,
        analysis_result: AnalysisResult,
        methodology_result: MethodologyResult,
        hypotheses: list[ExperimentHypothesis],
    ) -> tuple[list[ExperimentObjective], list[ExperimentPhase], list[DatasetUsage]]:
        start = time.monotonic()

        objectives = self._build_objectives(query, hypotheses)
        datasets = self._build_datasets(methodology_result)

        phases: list[ExperimentPhase] = []
        if self._llm and settings.enable_llm:
            phases = await self._llm_design(query, methodology_result, hypotheses)
        else:
            phases = self._default_phases(methodology_result)

        logger.info(
            "experiment design complete",
            extra={
                "objectives": len(objectives),
                "phases": len(phases),
                "datasets": len(datasets),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )

        return objectives, phases, datasets

    def _build_objectives(
        self,
        query: str,
        hypotheses: list[ExperimentHypothesis],
    ) -> list[ExperimentObjective]:
        objectives: list[ExperimentObjective] = []

        objectives.append(
            ExperimentObjective(
                objective=f"Validate primary hypothesis for: {query[:100]}",
                category="primary",
                priority=1,
                success_criteria="Hypothesis confirmed or rejected with statistical significance",
                rationale="Primary research objective derived from the query",
            )
        )

        for i, h in enumerate(hypotheses):
            if h.category == "primary":
                objectives.append(
                    ExperimentObjective(
                        objective=h.hypothesis[:150],
                        category="primary",
                        priority=i + 2,
                        success_criteria=h.validation_criteria
                        or "Statistical validation at p<0.05",
                        rationale=h.rationale or "Derived from primary hypothesis",
                    )
                )

        return objectives

    def _build_datasets(
        self,
        methodology_result: MethodologyResult,
    ) -> list[DatasetUsage]:
        datasets: list[DatasetUsage] = []
        for d in methodology_result.datasets:
            datasets.append(
                DatasetUsage(
                    dataset_name=d.dataset_name,
                    usage_type="training",
                    preprocessing="Standard preprocessing per dataset conventions",
                    split_ratios="80/10/10",
                    expected_size_mb=0.0,
                )
            )
        return datasets

    async def _llm_design(
        self,
        query: str,
        methodology_result: MethodologyResult,
        hypotheses: list[ExperimentHypothesis],
    ) -> list[ExperimentPhase]:
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
            datasets_text = (
                ", ".join(d.dataset_name for d in methodology_result.datasets[:5])
                if methodology_result.datasets
                else "none"
            )

            content = await self._llm.generate(
                prompt=_DESIGN_USER.format(
                    query=query,
                    hypotheses=hypo_text,
                    methods=methods_text,
                    datasets=datasets_text,
                    domain=methodology_result.profile.domain or "general",
                    max_phases=settings.max_experiment_phases,
                ),
                system_prompt=_DESIGN_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            return self._parse_phases(content)
        except Exception as exc:
            logger.warning("LLM experiment design failed", extra={"error": str(exc)})
            return self._default_phases(methodology_result)

    def _default_phases(
        self,
        methodology_result: MethodologyResult,
    ) -> list[ExperimentPhase]:
        return [
            ExperimentPhase(
                phase_id="phase_1",
                name="Data Preparation",
                description="Dataset acquisition, preprocessing, and splitting",
                phase_type="preparation",
                order=1,
                steps=[
                    ExecutionStep(
                        step_id="s1_1",
                        name="Dataset Acquisition",
                        description="Download and verify datasets",
                        step_type="data",
                        estimated_minutes=120,
                    ),
                    ExecutionStep(
                        step_id="s1_2",
                        name="Preprocessing",
                        description="Clean and preprocess data",
                        step_type="data",
                        estimated_minutes=180,
                    ),
                    ExecutionStep(
                        step_id="s1_3",
                        name="Data Splitting",
                        description="Split into train/val/test sets",
                        step_type="data",
                        estimated_minutes=30,
                    ),
                ],
                estimated_duration_minutes=330,
            ),
            ExperimentPhase(
                phase_id="phase_2",
                name="Implementation",
                description="Model implementation and setup",
                phase_type="implementation",
                order=2,
                steps=[
                    ExecutionStep(
                        step_id="s2_1",
                        name="Model Implementation",
                        description="Implement the proposed model architecture",
                        step_type="implementation",
                        estimated_minutes=480,
                    ),
                    ExecutionStep(
                        step_id="s2_2",
                        name="Baseline Implementation",
                        description="Implement baseline models for comparison",
                        step_type="implementation",
                        estimated_minutes=240,
                    ),
                ],
                estimated_duration_minutes=720,
            ),
            ExperimentPhase(
                phase_id="phase_3",
                name="Training",
                description="Model training and validation",
                phase_type="training",
                order=3,
                steps=[
                    ExecutionStep(
                        step_id="s3_1",
                        name="Model Training",
                        description="Train the model on training data",
                        step_type="training",
                        estimated_minutes=600,
                    ),
                    ExecutionStep(
                        step_id="s3_2",
                        name="Validation",
                        description="Validate on validation set",
                        step_type="validation",
                        estimated_minutes=120,
                    ),
                ],
                estimated_duration_minutes=720,
            ),
            ExperimentPhase(
                phase_id="phase_4",
                name="Evaluation",
                description="Comprehensive model evaluation",
                phase_type="evaluation",
                order=4,
                steps=[
                    ExecutionStep(
                        step_id="s4_1",
                        name="Test Evaluation",
                        description="Evaluate on held-out test set",
                        step_type="evaluation",
                        estimated_minutes=120,
                    ),
                    ExecutionStep(
                        step_id="s4_2",
                        name="Ablation Study",
                        description="Run ablation experiments",
                        step_type="analysis",
                        estimated_minutes=300,
                    ),
                ],
                estimated_duration_minutes=420,
            ),
        ]

    def _parse_phases(self, content: str) -> list[ExperimentPhase]:
        phases: list[ExperimentPhase] = []
        blocks = content.strip().split("\n\n")
        current_phase: dict[str, Any] = {}
        current_steps: list[ExecutionStep] = []
        step_count = 0
        phase_count = 0

        for block in blocks:
            block = block.strip()
            if not block:
                continue
            low = block.lower()

            if low.startswith("phase:"):
                if current_phase.get("name"):
                    phases.append(self._build_phase(current_phase, current_steps))
                phase_count += 1
                if phase_count > settings.max_experiment_phases:
                    break
                current_phase = {
                    "name": block.split(":", 1)[1].strip(),
                    "order": phase_count,
                }
                current_steps = []
                step_count = 0
            elif low.startswith("description:"):
                if "description" not in current_phase:
                    current_phase["description"] = block.split(":", 1)[1].strip()
            elif low.startswith("type:"):
                if "type" not in current_phase:
                    current_phase["type"] = block.split(":", 1)[1].strip().lower()
            elif low.startswith("step:"):
                step_count += 1
                if step_count > settings.max_experiment_steps:
                    continue
                parts = [p.strip() for p in block.split("|")]
                sid = parts[1] if len(parts) > 1 else f"s{phase_count}_{step_count}"
                sname = parts[2] if len(parts) > 2 else ""
                sdesc = parts[3] if len(parts) > 3 else ""
                stype = parts[4] if len(parts) > 4 else "processing"
                smin = 0
                if len(parts) > 5:
                    try:
                        smin = int(parts[5])
                    except (ValueError, TypeError):
                        smin = 60
                current_steps.append(
                    ExecutionStep(
                        step_id=sid,
                        name=sname,
                        description=sdesc,
                        step_type=stype,
                        estimated_minutes=smin,
                    )
                )

        if current_phase.get("name"):
            phases.append(self._build_phase(current_phase, current_steps))

        return phases

    def _build_phase(
        self,
        data: dict,
        steps: list[ExecutionStep],
    ) -> ExperimentPhase:
        total_minutes = sum(s.estimated_minutes for s in steps)
        return ExperimentPhase(
            phase_id=f"phase_{data.get('order', 1)}",
            name=data.get("name", ""),
            description=data.get("description", ""),
            phase_type=data.get("type", "preparation"),
            order=data.get("order", 1),
            steps=steps,
            estimated_duration_minutes=total_minutes,
        )
