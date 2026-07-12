from __future__ import annotations

import time

from app.core.logging import get_logger
from app.experiments.config import get_experiment_settings
from app.experiments.models import BaselineModel, BenchmarkExecution
from app.methodology.models import MethodologyResult
from app.rag.llm import RAGLLMProvider

logger = get_logger("experiments.baselines")
settings = get_experiment_settings()

_BASELINE_SYSTEM: str = (
    "You are a baseline and benchmark planning assistant. "
    "Recommend baseline models, benchmark datasets, and comparison strategies.\n\n"
    "For each baseline model:\n"
    "- Model name\n"
    "- Description\n"
    "- Expected performance range\n"
    "- Category: standard_baseline | state_of_the_art | ablation_variant | oracle\n"
    "- Rationale for inclusion\n\n"
    "For each benchmark execution:\n"
    "- Benchmark name\n"
    "- Dataset used\n"
    "- Metrics (comma-separated)\n"
    "- Comparison strategy\n"
    "- Ablation study design\n"
    "- Sensitivity analysis approach\n\n"
    "Format baselines:\n"
    "Baseline: <name>\n"
    "Description: <description>\n"
    "Expected Performance: <range>\n"
    "Category: <category>\n"
    "Rationale: <rationale>\n\n"
    "Format benchmarks:\n"
    "Benchmark: <name>\n"
    "Dataset: <dataset>\n"
    "Metrics: <comma-separated>\n"
    "Comparison: <strategy>\n"
    "Ablation: <design>\n"
    "Sensitivity: <approach>"
)

_BASELINE_USER: str = (
    "Research Query: {query}\n"
    "Methods: {methods}\n"
    "Datasets: {datasets}\n\n"
    "Recommend up to {baseline_limits} baselines and {benchmark_limits} benchmarks."
)


class BaselineBenchmarkPlanner:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def plan(
        self,
        query: str,
        methodology_result: MethodologyResult,
    ) -> tuple[list[BaselineModel], list[BenchmarkExecution]]:
        start = time.monotonic()

        baselines: list[BaselineModel] = self._default_baselines(methodology_result)
        benchmarks: list[BenchmarkExecution] = self._default_benchmarks(methodology_result)

        if self._llm and settings.enable_llm:
            llm_baselines, llm_benchmarks = await self._llm_plan(query, methodology_result)
            baselines = self._dedup_merge(baselines, llm_baselines)
            benchmarks = self._dedup_merge(benchmarks, llm_benchmarks)

        logger.info(
            "baseline benchmark planning complete",
            extra={
                "baselines": len(baselines),
                "benchmarks": len(benchmarks),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return baselines[: settings.baseline_limits], benchmarks[: settings.benchmark_limits]

    def _default_baselines(self, mr: MethodologyResult) -> list[BaselineModel]:
        bl: list[BaselineModel] = []

        if mr.methods:
            for m in mr.methods[:3]:
                bl.append(
                    BaselineModel(
                        model_name=f"Standard {m.method}",
                        description=f"Standard implementation of {m.method}",
                        expected_performance="Baseline performance range",
                        category="standard_baseline",
                        rationale=f"Recommended methodology: {m.rationale[:80]}" if m.rationale else "",
                    )
                )

        bl.append(
            BaselineModel(
                model_name="Random Baseline",
                description="Random prediction baseline for comparison",
                expected_performance="Lower bound of expected performance",
                category="standard_baseline",
                rationale="Minimum performance threshold",
            )
        )
        return bl

    def _default_benchmarks(self, mr: MethodologyResult) -> list[BenchmarkExecution]:
        benchmarks: list[BenchmarkExecution] = []
        for b in mr.benchmarks[:3]:
            benchmarks.append(
                BenchmarkExecution(
                    benchmark_name=b.benchmark_name,
                    dataset=b.benchmark_name,
                    metrics=["accuracy", "f1"],
                    comparison_strategy="direct_comparison",
                    ablation="Remove key components",
                    sensitivity="Hyperparameter variation",
                )
            )
        return benchmarks

    async def _llm_plan(
        self,
        query: str,
        mr: MethodologyResult,
    ) -> tuple[list[BaselineModel], list[BenchmarkExecution]]:
        try:
            methods_text = ", ".join(m.method for m in mr.methods[:5]) if mr.methods else "none"
            datasets_text = ", ".join(d.dataset_name for d in mr.datasets[:5]) if mr.datasets else "none"

            content = await self._llm.generate(
                prompt=_BASELINE_USER.format(
                    query=query,
                    methods=methods_text,
                    datasets=datasets_text,
                    baseline_limits=settings.baseline_limits,
                    benchmark_limits=settings.benchmark_limits,
                ),
                system_prompt=_BASELINE_SYSTEM,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            return self._parse_content(content)
        except Exception as exc:
            logger.warning("LLM baseline planning failed", extra={"error": str(exc)})
            return [], []

    def _parse_content(
        self,
        content: str,
    ) -> tuple[list[BaselineModel], list[BenchmarkExecution]]:
        import re
        baselines: list[BaselineModel] = []
        benchmarks: list[BenchmarkExecution] = []
        current_baseline: dict = {}
        current_benchmark: dict = {}
        in_baseline = False
        in_benchmark = False

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            low = line.lower()

            if low.startswith("baseline:"):
                if current_baseline.get("name"):
                    baselines.append(self._build_baseline(current_baseline))
                current_baseline = {"name": line.split(":", 1)[1].strip()}
                current_benchmark = {}
                in_baseline = True
                in_benchmark = False
            elif low.startswith("benchmark:"):
                if current_benchmark.get("name"):
                    benchmarks.append(self._build_benchmark(current_benchmark))
                current_benchmark = {"name": line.split(":", 1)[1].strip()}
                current_baseline = {}
                in_baseline = False
                in_benchmark = True
            elif in_baseline:
                if low.startswith("description:"):
                    current_baseline["description"] = line.split(":", 1)[1].strip()
                elif low.startswith("expected performance:"):
                    current_baseline["expected"] = line.split(":", 1)[1].strip()
                elif low.startswith("category:"):
                    current_baseline["category"] = line.split(":", 1)[1].strip().lower()
                elif low.startswith("rationale:"):
                    current_baseline["rationale"] = line.split(":", 1)[1].strip()
            elif in_benchmark:
                if low.startswith("dataset:"):
                    current_benchmark["dataset"] = line.split(":", 1)[1].strip()
                elif low.startswith("metrics:"):
                    current_benchmark["metrics"] = [m.strip() for m in line.split(":", 1)[1].split(",") if m.strip()]
                elif low.startswith("comparison:"):
                    current_benchmark["comparison"] = line.split(":", 1)[1].strip()
                elif low.startswith("ablation:"):
                    current_benchmark["ablation"] = line.split(":", 1)[1].strip()
                elif low.startswith("sensitivity:"):
                    current_benchmark["sensitivity"] = line.split(":", 1)[1].strip()

        if current_baseline.get("name"):
            baselines.append(self._build_baseline(current_baseline))
        if current_benchmark.get("name"):
            benchmarks.append(self._build_benchmark(current_benchmark))

        return baselines, benchmarks

    def _build_baseline(self, data: dict) -> BaselineModel:
        return BaselineModel(
            model_name=data.get("name", ""),
            description=data.get("description", ""),
            expected_performance=data.get("expected", ""),
            category=data.get("category", "standard_baseline"),
            rationale=data.get("rationale", ""),
        )

    def _build_benchmark(self, data: dict) -> BenchmarkExecution:
        return BenchmarkExecution(
            benchmark_name=data.get("name", ""),
            dataset=data.get("dataset", ""),
            metrics=data.get("metrics", []),
            comparison_strategy=data.get("comparison", ""),
            ablation=data.get("ablation", ""),
            sensitivity=data.get("sensitivity", ""),
        )

    def _dedup_merge(self, defaults: list, llm_items: list) -> list:
        seen: set[str] = set()
        merged: list = []
        for item in defaults + llm_items:
            key = ""
            if isinstance(item, BaselineModel):
                key = item.model_name.lower()
            elif isinstance(item, BenchmarkExecution):
                key = item.benchmark_name.lower()
            if key and key not in seen:
                seen.add(key)
                merged.append(item)
        return merged
