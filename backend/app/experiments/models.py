from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ExperimentObjective:
    objective: str = ""
    category: str = "primary"
    priority: int = 5
    success_criteria: str = ""
    rationale: str = ""


@dataclass
class ExperimentHypothesis:
    hypothesis: str = ""
    rationale: str = ""
    supporting_evidence: list[str] = field(default_factory=list)
    confidence: float = 0.5
    validation_criteria: str = ""
    category: str = "primary"
    status: str = "proposed"


@dataclass
class VariableDefinition:
    name: str = ""
    variable_type: str = "independent"
    description: str = ""
    expected_effect: str = ""
    reasoning: str = ""
    possible_values: list[str] = field(default_factory=list)


@dataclass
class DatasetUsage:
    dataset_name: str = ""
    usage_type: str = "training"
    preprocessing: str = ""
    split_ratios: str = ""
    expected_size_mb: float = 0.0


@dataclass
class EvaluationMetric:
    name: str = ""
    description: str = ""
    expected_value: float = 0.0
    threshold: float = 0.0
    direction: str = "higher_is_better"
    statistical_test: str = ""


@dataclass
class BaselineModel:
    model_name: str = ""
    description: str = ""
    expected_performance: str = ""
    category: str = "standard_baseline"
    rationale: str = ""


@dataclass
class BenchmarkExecution:
    benchmark_name: str = ""
    dataset: str = ""
    metrics: list[str] = field(default_factory=list)
    comparison_strategy: str = ""
    ablation: str = ""
    sensitivity: str = ""


@dataclass
class ExecutionStep:
    step_id: str = ""
    name: str = ""
    description: str = ""
    step_type: str = "processing"
    estimated_minutes: int = 0
    dependencies: list[str] = field(default_factory=list)
    command: str = ""
    expected_output: str = ""


@dataclass
class ExperimentPhase:
    phase_id: str = ""
    name: str = ""
    description: str = ""
    phase_type: str = "preparation"
    order: int = 0
    steps: list[ExecutionStep] = field(default_factory=list)
    estimated_duration_minutes: int = 0
    dependencies: list[str] = field(default_factory=list)


@dataclass
class ExpectedOutcome:
    outcome: str = ""
    category: str = "primary"
    likelihood: float = 0.5
    impact: str = "medium"
    evidence: list[str] = field(default_factory=list)


@dataclass
class RiskMitigation:
    risk: str = ""
    category: str = "technical"
    severity: str = "medium"
    likelihood: float = 0.5
    impact: str = "medium"
    mitigation: str = ""
    fallback: str = ""
    status: str = "identified"


@dataclass
class ExperimentTimeline:
    total_estimated_days: int = 0
    phases: list[str] = field(default_factory=list)
    milestones: list[str] = field(default_factory=list)
    critical_path: list[str] = field(default_factory=list)


@dataclass
class ResourceEstimate:
    compute_hours: int = 0
    gpu_hours: int = 0
    cpu_cores: int = 0
    memory_gb: int = 0
    storage_gb: int = 0
    estimated_cost_usd: float = 0.0
    software_dependencies: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class ExperimentRequest:
    query: str
    analysis_result: Any
    methodology_result: Any
    domain: str | None = None
    complexity: str | None = None
    user_id: Any | None = None
    project_id: Any | None = None


@dataclass
class ExperimentStatistics:
    total_hypotheses: int = 0
    total_phases: int = 0
    total_steps: int = 0
    total_variables: int = 0
    total_baselines: int = 0
    total_risks: int = 0
    total_metrics: int = 0
    estimated_days: int = 0
    overall_confidence: float = 0.0


@dataclass
class ExperimentValidationReport:
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_baselines: list[str] = field(default_factory=list)
    missing_metrics: list[str] = field(default_factory=list)
    unsupported_hypotheses: list[str] = field(default_factory=list)
    inconsistent_variables: list[str] = field(default_factory=list)
    incomplete_protocols: list[str] = field(default_factory=list)
    reproducibility_issues: list[str] = field(default_factory=list)


@dataclass
class ExperimentMetadata:
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: float = 0.0
    model: str = ""
    complexity: str = "moderate"
    validation_passed: bool = True
    validation_errors: list[str] = field(default_factory=list)


@dataclass
class ExperimentPlan:
    query: str = ""
    objectives: list[ExperimentObjective] = field(default_factory=list)
    hypotheses: list[ExperimentHypothesis] = field(default_factory=list)
    phases: list[ExperimentPhase] = field(default_factory=list)
    variables: list[VariableDefinition] = field(default_factory=list)
    datasets: list[DatasetUsage] = field(default_factory=list)
    benchmarks: list[BenchmarkExecution] = field(default_factory=list)
    baselines: list[BaselineModel] = field(default_factory=list)
    evaluation_metrics: list[EvaluationMetric] = field(default_factory=list)
    expected_outcomes: list[ExpectedOutcome] = field(default_factory=list)
    risks: list[RiskMitigation] = field(default_factory=list)
    timeline: ExperimentTimeline = field(default_factory=ExperimentTimeline)
    resources: ResourceEstimate = field(default_factory=ResourceEstimate)
    statistics: ExperimentStatistics = field(default_factory=ExperimentStatistics)
    metadata: ExperimentMetadata = field(default_factory=ExperimentMetadata)
    validation: ExperimentValidationReport | None = None
