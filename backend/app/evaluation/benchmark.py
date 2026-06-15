from __future__ import annotations

import re
import uuid
from typing import Any

from app.core.logging import get_logger
from app.evaluation.scorecard import generate_scorecard


logger = get_logger("evaluation.benchmark")


class BenchmarkDefinition:
    """A gold-standard benchmark for evaluating research quality."""

    def __init__(
        self,
        name: str,
        query: str,
        expected_findings: list[str],
        expected_subtopics: list[str],
        expected_references: list[str],
        expected_quality_score: float | None = None,
        description: str = "",
        tags: list[str] | None = None,
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.query = query
        self.expected_findings = expected_findings
        self.expected_subtopics = expected_subtopics
        self.expected_references = expected_references
        self.expected_quality_score = expected_quality_score
        self.description = description
        self.tags = tags or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "query": self.query,
            "expected_findings": self.expected_findings,
            "expected_subtopics": self.expected_subtopics,
            "expected_references": self.expected_references,
            "expected_quality_score": self.expected_quality_score,
            "description": self.description,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkDefinition":
        inst = cls(
            name=data["name"],
            query=data["query"],
            expected_findings=data["expected_findings"],
            expected_subtopics=data["expected_subtopics"],
            expected_references=data["expected_references"],
            expected_quality_score=data.get("expected_quality_score"),
            description=data.get("description", ""),
            tags=data.get("tags"),
        )
        inst.id = data.get("id", inst.id)
        return inst


BUILTIN_BENCHMARKS: list[BenchmarkDefinition] = [
    BenchmarkDefinition(
        name="ai_safety_research",
        query="What are the key challenges in AI safety research?",
        expected_findings=[
            "alignment problem",
            "reward hacking",
            "scalable oversight",
            "value learning",
        ],
        expected_subtopics=[
            "alignment",
            "robustness",
            "monitoring",
            "governance",
        ],
        expected_references=[
            "https://arxiv.org/abs/1606.06565",
        ],
        expected_quality_score=75.0,
        description="Benchmark for AI safety research coverage",
        tags=["ai", "safety", "alignment"],
    ),
    BenchmarkDefinition(
        name="climate_change_impact",
        query="What are the impacts of climate change on global food security?",
        expected_findings=[
            "crop yield reduction",
            "supply chain disruption",
            "nutritional quality decline",
        ],
        expected_subtopics=[
            "agriculture",
            "supply chains",
            "food access",
        ],
        expected_references=[
            "https://ipcc.ch/",
        ],
        expected_quality_score=70.0,
        description="Benchmark for climate change food security research",
        tags=["climate", "food", "security"],
    ),
    BenchmarkDefinition(
        name="quantum_computing",
        query="What is the current state of quantum computing error correction?",
        expected_findings=[
            "surface codes",
            "logical qubits",
            "error threshold",
            "fault tolerance",
        ],
        expected_subtopics=[
            "error correction codes",
            "physical qubits",
            "logical qubits",
            "threshold theorem",
        ],
        expected_references=[
            "https://arxiv.org/abs/quant-ph/",
        ],
        expected_quality_score=70.0,
        description="Benchmark for quantum computing error correction coverage",
        tags=["quantum", "computing", "error-correction"],
    ),
]


class BenchmarkRunner:
    """Runs golden benchmarks against evaluation results."""

    def __init__(self, benchmarks: list[BenchmarkDefinition] | None = None):
        self._benchmarks = {b.name: b for b in (benchmarks or BUILTIN_BENCHMARKS)}

    def list_benchmarks(self) -> list[dict[str, Any]]:
        return [b.to_dict() for b in self._benchmarks.values()]

    def get_benchmark(self, name: str) -> BenchmarkDefinition | None:
        return self._benchmarks.get(name)

    async def run_benchmark(
        self,
        benchmark_name: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        benchmark = self.get_benchmark(benchmark_name)
        if benchmark is None:
            raise ValueError(f"Unknown benchmark: {benchmark_name}")

        findings = _collect_findings(state)
        subtopics = _collect_subtopics(state)
        references = _collect_references(state)

        finding_match_rate = self.compute_match_rate(benchmark.expected_findings, findings)
        subtopic_match_rate = self.compute_match_rate(benchmark.expected_subtopics, subtopics)
        reference_match_rate = self.compute_reference_match_rate(
            benchmark.expected_references, references
        )

        overall_benchmark_score = round(
            finding_match_rate * 0.4 + subtopic_match_rate * 0.3 + reference_match_rate * 0.3,
            2,
        )

        scorecard = None
        if state.get("summaries") or state.get("generated_report"):
            try:
                scorecard = generate_scorecard(state)
            except Exception:
                logger.exception("Failed to generate scorecard for benchmark")

        return {
            "benchmark": benchmark.to_dict(),
            "scores": scorecard,
            "finding_match_rate": finding_match_rate,
            "subtopic_match_rate": subtopic_match_rate,
            "reference_match_rate": reference_match_rate,
            "overall_benchmark_score": overall_benchmark_score,
            "passed": overall_benchmark_score >= 60,
        }

    @staticmethod
    def compute_match_rate(
        expected: list[str],
        actual: list[str],
    ) -> float:
        if not expected:
            return 100.0
        if not actual:
            return 0.0

        matched = 0
        for exp_item in expected:
            exp_words = _significant_words(exp_item)
            if not exp_words:
                matched += 1
                continue
            found = False
            for act_item in actual:
                act_words = _significant_words(act_item)
                if not act_words:
                    continue
                overlap = len(set(exp_words) & set(act_words))
                if overlap / len(exp_words) >= 0.4:
                    found = True
                    break
            if found:
                matched += 1

        return round((matched / len(expected)) * 100, 2)

    @staticmethod
    def compute_reference_match_rate(
        expected_refs: list[str],
        actual_refs: list[str],
    ) -> float:
        if not expected_refs:
            return 100.0
        if not actual_refs:
            return 0.0

        matched = 0
        for exp_ref in expected_refs:
            exp_normalized = _normalize_reference(exp_ref)
            if not exp_normalized:
                matched += 1
                continue
            found = False
            for act_ref in actual_refs:
                act_normalized = _normalize_reference(act_ref)
                if exp_normalized in act_normalized or act_normalized in exp_normalized:
                    found = True
                    break
            if found:
                matched += 1

        return round((matched / len(expected_refs)) * 100, 2)


def _collect_findings(state: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    report = state.get("generated_report")
    if isinstance(report, str):
        findings.append(report)
    elif isinstance(report, dict):
        report_text = report.get("executive_summary") or report.get("conclusion") or ""
        if report_text:
            findings.append(report_text)
        for sec in report.get("sections", []):
            if isinstance(sec, dict):
                st = sec.get("summary") or ""
                if st:
                    findings.append(st)
                for kf in sec.get("key_findings", []):
                    if isinstance(kf, str):
                        findings.append(kf)
    for s in state.get("summaries", []):
        content = s.get("content") or s.get("summary") or s.get("executive_summary") or ""
        if content:
            findings.append(content)
    for d in state.get("retrieved_documents", []):
        content = d.get("content") or d.get("text") or ""
        if content:
            findings.append(content)
    return findings


def _collect_subtopics(state: dict[str, Any]) -> list[str]:
    subtopics: list[str] = []
    gaps = state.get("research_gaps", [])
    for gap in gaps:
        label = gap.get("subtopic") or gap.get("area") or gap.get("description") or ""
        if label:
            subtopics.append(label)
    planner = state.get("planner_output", "")
    if planner:
        subtopics.append(planner)
    return subtopics


def _collect_references(state: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for d in state.get("retrieved_documents", []):
        source = d.get("source") or d.get("url") or d.get("link") or ""
        if source:
            refs.append(source)
    for s in state.get("summaries", []):
        for ref in s.get("references", s.get("sources", [])):
            if isinstance(ref, str):
                refs.append(ref)
            elif isinstance(ref, dict):
                refs.append(ref.get("url") or ref.get("source") or str(ref))
    return refs


def _significant_words(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z]\w*", text.lower())
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "can", "could", "may", "might", "shall", "should", "not", "no", "nor",
        "it", "its", "this", "that", "these", "those", "what", "which", "who",
        "how", "when", "where", "why",
    }
    return [w for w in words if w not in stop_words and len(w) > 1]


def _normalize_reference(ref: str) -> str:
    ref = ref.strip().lower()
    ref = re.sub(r"^https?://", "", ref)
    ref = ref.rstrip("/")
    return ref
