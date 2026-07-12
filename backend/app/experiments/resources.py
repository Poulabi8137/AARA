from __future__ import annotations

import time

from app.core.logging import get_logger
from app.experiments.config import get_experiment_settings
from app.experiments.models import ExperimentPhase, ResourceEstimate
from app.methodology.models import MethodologyResult
from app.rag.llm import RAGLLMProvider

logger = get_logger("experiments.resources")
settings = get_experiment_settings()

_RESOURCE_SYSTEM: str = (
    "You are a research resource estimation assistant. "
    "Estimate compute, storage, and runtime requirements for the experiment.\n\n"
    "Provide:\n"
    "- Total compute hours\n"
    "- GPU hours (if applicable)\n"
    "- CPU cores needed\n"
    "- Memory (GB)\n"
    "- Storage (GB)\n"
    "- Estimated cost in USD (optional)\n"
    "- Software dependencies (comma-separated)\n"
    "- Additional notes\n\n"
    "Format:\n"
    "Compute Hours: <number>\n"
    "GPU Hours: <number>\n"
    "CPU Cores: <number>\n"
    "Memory GB: <number>\n"
    "Storage GB: <number>\n"
    "Estimated Cost USD: <number>\n"
    "Dependencies: <comma-separated>\n"
    "Notes: <text>"
)

_RESOURCE_USER: str = (
    "Research Query: {query}\n"
    "Number of Phases: {num_phases}\n"
    "Methods: {methods}\n"
    "Datasets: {datasets}\n"
    "Total Estimated Minutes: {total_minutes}\n\n"
    "Estimate resource requirements."
)


class ResourcePlanner:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def estimate(
        self,
        query: str,
        methodology_result: MethodologyResult,
        phases: list[ExperimentPhase],
    ) -> ResourceEstimate:
        start = time.monotonic()

        rule_based = self._rule_based(methodology_result, phases)

        llm_estimate: ResourceEstimate | None = None
        if self._llm and settings.enable_llm:
            llm_estimate = await self._llm_estimate(query, methodology_result, phases)

        merged = self._merge_estimates(rule_based, llm_estimate)

        logger.info(
            "resource estimation complete",
            extra={
                "compute_hours": merged.compute_hours,
                "gpu_hours": merged.gpu_hours,
                "storage_gb": merged.storage_gb,
                "estimated_cost_usd": merged.estimated_cost_usd,
                "dependencies": len(merged.software_dependencies),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )

        return merged

    def _rule_based(
        self,
        methodology_result: MethodologyResult,
        phases: list[ExperimentPhase],
    ) -> ResourceEstimate:
        total_minutes = sum(p.estimated_duration_minutes for p in phases)
        compute_hours = max(1, total_minutes // 60)
        has_deep_learning = any(
            "deep" in m.method.lower() or "transformer" in m.method.lower()
            for m in methodology_result.methods
        )

        return ResourceEstimate(
            compute_hours=compute_hours,
            gpu_hours=compute_hours if has_deep_learning else 0,
            cpu_cores=8,
            memory_gb=32 if has_deep_learning else 16,
            storage_gb=50,
            estimated_cost_usd=compute_hours * 1.5 if has_deep_learning else 0.0,
            software_dependencies=[
                "python",
                "pytorch" if has_deep_learning else "scikit-learn",
            ],
            notes=f"Estimated based on {len(phases)} phases totaling {total_minutes} minutes",
        )

    async def _llm_estimate(
        self,
        query: str,
        mr: MethodologyResult,
        phases: list[ExperimentPhase],
    ) -> ResourceEstimate | None:
        try:
            methods_text = (
                ", ".join(m.method for m in mr.methods[:5]) if mr.methods else "none"
            )
            datasets_text = (
                ", ".join(d.dataset_name for d in mr.datasets[:5])
                if mr.datasets
                else "none"
            )
            total_minutes = sum(p.estimated_duration_minutes for p in phases)

            content = await self._llm.generate(
                prompt=_RESOURCE_USER.format(
                    query=query,
                    num_phases=len(phases),
                    methods=methods_text,
                    datasets=datasets_text,
                    total_minutes=total_minutes,
                ),
                system_prompt=_RESOURCE_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            return self._parse_estimate(content)
        except Exception as exc:
            logger.warning("LLM resource estimation failed", extra={"error": str(exc)})
            return None

    def _parse_estimate(self, content: str) -> ResourceEstimate:
        result = ResourceEstimate()
        for line in content.split("\n"):
            line = line.strip()
            low = line.lower()
            try:
                if low.startswith("compute hours:"):
                    result.compute_hours = int(float(line.split(":")[1].strip()))
                elif low.startswith("gpu hours:"):
                    result.gpu_hours = int(float(line.split(":")[1].strip()))
                elif low.startswith("cpu cores:"):
                    result.cpu_cores = int(float(line.split(":")[1].strip()))
                elif low.startswith("memory gb:"):
                    result.memory_gb = int(float(line.split(":")[1].strip()))
                elif low.startswith("storage gb:"):
                    result.storage_gb = int(float(line.split(":")[1].strip()))
                elif low.startswith("estimated cost usd:"):
                    result.estimated_cost_usd = float(line.split(":")[1].strip())
                elif low.startswith("dependencies:"):
                    result.software_dependencies = [
                        d.strip() for d in line.split(":")[1].split(",") if d.strip()
                    ]
                elif low.startswith("notes:"):
                    result.notes = line.split(":", 1)[1].strip()
            except (ValueError, TypeError, IndexError):
                continue
        return result

    def _merge_estimates(
        self,
        rule_based: ResourceEstimate,
        llm_estimate: ResourceEstimate | None,
    ) -> ResourceEstimate:
        if not llm_estimate:
            return rule_based

        deps = list(
            set(rule_based.software_dependencies + llm_estimate.software_dependencies)
        )
        return ResourceEstimate(
            compute_hours=max(rule_based.compute_hours, llm_estimate.compute_hours),
            gpu_hours=max(rule_based.gpu_hours, llm_estimate.gpu_hours),
            cpu_cores=max(rule_based.cpu_cores, llm_estimate.cpu_cores),
            memory_gb=max(rule_based.memory_gb, llm_estimate.memory_gb),
            storage_gb=max(rule_based.storage_gb, llm_estimate.storage_gb),
            estimated_cost_usd=max(
                rule_based.estimated_cost_usd, llm_estimate.estimated_cost_usd
            ),
            software_dependencies=deps,
            notes=f"Rule-based: {rule_based.notes} | LLM: {llm_estimate.notes}"
            if llm_estimate.notes
            else rule_based.notes,
        )
