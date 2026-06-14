from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class GapType(str, Enum):
    MISSING_SUBTOPIC = "MISSING_SUBTOPIC"
    LOW_EVIDENCE = "LOW_EVIDENCE"
    LOW_CITATION_COVERAGE = "LOW_CITATION_COVERAGE"
    CONTRADICTION = "CONTRADICTION"
    OUTDATED_INFORMATION = "OUTDATED_INFORMATION"
    MISSING_RISK_ANALYSIS = "MISSING_RISK_ANALYSIS"
    MISSING_PRIORITY_AREA = "MISSING_PRIORITY_AREA"
    MISSING_RESEARCH_QUESTION = "MISSING_RESEARCH_QUESTION"
    INSUFFICIENT_SOURCE_DIVERSITY = "INSUFFICIENT_SOURCE_DIVERSITY"
    LOW_CONFIDENCE_SUMMARY = "LOW_CONFIDENCE_SUMMARY"


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RemediationSuggestion(BaseModel):
    recommended_queries: list[str] = Field(default_factory=list)
    recommended_sources: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class ResearchGap(BaseModel):
    gap_id: str
    gap_type: GapType
    description: str
    severity: SeverityLevel
    affected_subtopics: list[str] = Field(default_factory=list)
    supporting_evidence: str = ""
    remediation: RemediationSuggestion = Field(default_factory=RemediationSuggestion)
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)


class CoverageMetrics(BaseModel):
    coverage_score: float = Field(default=0.0, ge=0.0, le=100.0)
    question_completion_score: float = Field(default=0.0, ge=0.0, le=100.0)
    risk_coverage_score: float = Field(default=0.0, ge=0.0, le=100.0)
    priority_coverage_score: float = Field(default=0.0, ge=0.0, le=100.0)
    research_completeness_score: float = Field(default=0.0, ge=0.0, le=100.0)
    source_diversity_score: float = Field(default=0.0, ge=0.0, le=100.0)
    average_confidence_score: float = Field(default=0.0, ge=0.0, le=100.0)
    total_gaps: int = 0
    critical_gaps: int = 0
    high_gaps: int = 0
    medium_gaps: int = 0
    low_gaps: int = 0
    subtopics_planned: int = 0
    subtopics_covered: int = 0
    questions_total: int = 0
    questions_answered: int = 0
    priority_areas_total: int = 0
    priority_areas_covered: int = 0
    risk_areas_total: int = 0
    risk_areas_covered: int = 0


class GapAnalysisResult(BaseModel):
    gaps: list[ResearchGap] = Field(default_factory=list)
    metrics: CoverageMetrics = Field(default_factory=CoverageMetrics)
    question_mapping: dict[str, str] = Field(default_factory=dict)
    priority_mapping: dict[str, str] = Field(default_factory=dict)
    risk_mapping: dict[str, str] = Field(default_factory=dict)
    latency_seconds: float = 0.0
    used_fallback: bool = False
