from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class MethodologyRequest:
    query: str
    analysis_result: Any
    domain: str | None = None
    project_type: str | None = None
    user_id: Any | None = None
    project_id: Any | None = None


@dataclass
class MethodologyProfile:
    domain: str = ""
    complexity: str = "moderate"
    evidence_quality: float = 0.0
    research_goal: str = ""


@dataclass
class ResearchMethod:
    method: str = ""
    confidence: float = 0.5
    rationale: str = ""
    supporting_evidence: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class DatasetRecommendation:
    dataset_name: str = ""
    domain_relevance: float = 0.5
    diversity: float = 0.5
    size_category: str = "medium"
    quality: float = 0.5
    licensing: str = "unknown"
    availability: str = "unknown"
    maturity: str = "established"
    confidence: float = 0.5
    rationale: str = ""


@dataclass
class BenchmarkRecommendation:
    benchmark_name: str = ""
    category: str = "standard"
    relevance: float = 0.5
    rationale: str = ""
    confidence: float = 0.5


@dataclass
class EvaluationProtocol:
    metrics: list[str] = field(default_factory=list)
    baselines: list[str] = field(default_factory=list)
    comparison_methods: list[str] = field(default_factory=list)
    validation_strategy: str = ""
    reproducibility_steps: list[str] = field(default_factory=list)


@dataclass
class ValidationStrategy:
    strategy: str = ""
    description: str = ""
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    confidence: float = 0.5


@dataclass
class RiskAssessment:
    risk: str = ""
    category: str = "general"
    severity: str = "medium"
    mitigation: str = ""
    confidence: float = 0.5


@dataclass
class BestPractice:
    practice: str = ""
    category: str = "general"
    rationale: str = ""
    source: str = ""


@dataclass
class MethodologyStatistics:
    total_methods: int = 0
    total_datasets: int = 0
    total_benchmarks: int = 0
    total_risks: int = 0
    total_practices: int = 0
    overall_confidence: float = 0.0


@dataclass
class MethodologyValidationReport:
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_datasets: list[str] = field(default_factory=list)
    missing_benchmarks: list[str] = field(default_factory=list)
    weak_evaluation: list[str] = field(default_factory=list)
    incomplete_validation: list[str] = field(default_factory=list)


@dataclass
class MethodologyMetadata:
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    duration_ms: float = 0.0
    model: str = ""
    validation_passed: bool = True
    validation_errors: list[str] = field(default_factory=list)


@dataclass
class MethodologyResult:
    profile: MethodologyProfile = field(default_factory=MethodologyProfile)
    methods: list[ResearchMethod] = field(default_factory=list)
    datasets: list[DatasetRecommendation] = field(default_factory=list)
    benchmarks: list[BenchmarkRecommendation] = field(default_factory=list)
    protocol: EvaluationProtocol | None = None
    validation_strategies: list[ValidationStrategy] = field(default_factory=list)
    risks: list[RiskAssessment] = field(default_factory=list)
    best_practices: list[BestPractice] = field(default_factory=list)
    statistics: MethodologyStatistics = field(default_factory=MethodologyStatistics)
    metadata: MethodologyMetadata = field(default_factory=MethodologyMetadata)
    validation: MethodologyValidationReport | None = None
