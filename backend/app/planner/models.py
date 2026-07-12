from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.rag.models import RetrievalStrategy, SearchIntent, SourceType


class TaskComplexity(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class TaskType(str, Enum):
    LITERATURE_REVIEW = "literature_review"
    SURVEY = "survey"
    COMPARISON = "comparison"
    EXPERIMENT_PLANNING = "experiment_planning"
    BENCHMARK_ANALYSIS = "benchmark_analysis"
    DATASET_DISCOVERY = "dataset_discovery"
    PAPER_ANALYSIS = "paper_analysis"
    RESEARCH_SYNTHESIS = "research_synthesis"
    METHODOLOGY_DESIGN = "methodology_design"


class TaskStatus(str, Enum):
    PENDING = "pending"
    BLOCKED = "blocked"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class DependencyType(str, Enum):
    BLOCKING = "blocking"
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


class AgentType(str, Enum):
    RETRIEVER = "retriever"
    SUMMARIZER = "summarizer"
    ANALYZER = "analyzer"
    METHODOLOGY = "methodology"
    EXPERIMENT = "experiment"
    CITATION = "citation"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    AI_MENTOR = "ai_mentor"


class ResearchStrategyType(str, Enum):
    LITERATURE_REVIEW = "literature_review"
    COMPARATIVE_ANALYSIS = "comparative_analysis"
    EXPERIMENTAL = "experimental"
    SURVEY = "survey"
    BENCHMARK = "benchmark"
    METHODOLOGY = "methodology"
    NOVELTY_INVESTIGATION = "novelty_investigation"
    GENERAL = "general"


@dataclass
class RetrievalPlan:
    collections: list[SourceType] = field(default_factory=list)
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    depth: int = 5
    confidence_threshold: float = 0.3
    citation_required: bool = False
    memory_usage: bool = True
    external_search: bool = False


@dataclass
class ResearchTask:
    task_id: str
    type: TaskType
    objective: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)
    expected_output: str = ""
    priority: int = 5
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: AgentType | None = None
    retrieval_plan: RetrievalPlan | None = None


@dataclass
class TaskDependency:
    task_id: str
    depends_on: str
    dependency_type: DependencyType = DependencyType.BLOCKING


@dataclass
class ResearchGoal:
    objective: str
    intent: SearchIntent = SearchIntent.FACTUAL
    complexity: TaskComplexity = TaskComplexity.MODERATE
    required_outputs: list[str] = field(default_factory=list)
    estimated_difficulty: float = 0.5
    ambiguity_score: float = 0.0
    missing_information: list[str] = field(default_factory=list)


@dataclass
class PlanningContext:
    user_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    previous_plans: list[str] = field(default_factory=list)


@dataclass
class DependencyGraph:
    nodes: set[str] = field(default_factory=set)
    edges: dict[str, list[TaskDependency]] = field(default_factory=dict)
    execution_order: list[list[str]] = field(default_factory=list)
    parallelizable: list[list[str]] = field(default_factory=list)
    is_valid: bool = True
    circular_dependencies: list[list[str]] = field(default_factory=list)


@dataclass
class ExecutionStep:
    task_id: str
    agent_type: AgentType
    task_type: TaskType
    objective: str
    priority: int = 5
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent_id: str = ""


@dataclass
class PlanningMetadata:
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: float = 0.0
    strategy_used: ResearchStrategyType = ResearchStrategyType.GENERAL
    validation_passed: bool = True
    validation_errors: list[str] = field(default_factory=list)
    plan_version: str = "1.0"


@dataclass
class ExecutionPlan:
    plan_id: str
    goal: ResearchGoal
    tasks: list[ResearchTask] = field(default_factory=list)
    dependencies: list[TaskDependency] = field(default_factory=list)
    dependency_graph: DependencyGraph = field(default_factory=DependencyGraph)
    steps: list[ExecutionStep] = field(default_factory=list)
    strategy: ResearchStrategyType = ResearchStrategyType.GENERAL
    metadata: PlanningMetadata = field(default_factory=PlanningMetadata)
    context: PlanningContext = field(default_factory=PlanningContext)


@dataclass
class ValidationReport:
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_dependencies: list[str] = field(default_factory=list)
    invalid_orderings: list[str] = field(default_factory=list)
    duplicate_tasks: list[str] = field(default_factory=list)
    unreachable_tasks: list[str] = field(default_factory=list)
    circular_dependencies: list[list[str]] = field(default_factory=list)
    incomplete_objectives: list[str] = field(default_factory=list)


@dataclass
class PlanningResult:
    plan: ExecutionPlan
    validation: ValidationReport
    metadata: PlanningMetadata
