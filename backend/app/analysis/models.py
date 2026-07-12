from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AnalysisSectionType(str, Enum):
    CONSENSUS = "consensus"
    CONTRADICTION = "contradiction"
    TRENDS = "trends"
    LIMITATIONS = "limitations"
    RECOMMENDATIONS = "recommendations"
    CONFIDENCE = "confidence"
    RELATIONSHIPS = "relationships"


@dataclass
class AnalysisRequest:
    query: str
    summary_result: Any
    section_types: list[AnalysisSectionType] | None = None
    user_id: Any | None = None
    project_id: Any | None = None


@dataclass
class AnalysisInsight:
    insight: str
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.5
    category: str = "general"


@dataclass
class AnalysisSection:
    type: AnalysisSectionType
    title: str
    content: str
    insights: list[AnalysisInsight] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class ConsensusResult:
    statement: str
    supporting_sources: list[str] = field(default_factory=list)
    evidence_count: int = 0
    confidence: float = 0.5
    category: str = "general"


@dataclass
class ConflictingSide:
    position: str
    sources: list[str] = field(default_factory=list)
    methodology: str | None = None


@dataclass
class Contradiction:
    statement: str
    conflicting_sides: list[ConflictingSide] = field(default_factory=list)
    resolution: str | None = None
    severity: str = "medium"


@dataclass
class ResearchTrend:
    trend: str
    direction: str = "emerging"
    evidence: list[str] = field(default_factory=list)
    time_range: tuple[str, str] = ("", "")
    confidence: float = 0.5


@dataclass
class Limitation:
    limitation: str
    category: str = "general"
    sources: list[str] = field(default_factory=list)
    severity: str = "medium"


@dataclass
class Recommendation:
    recommendation: str
    category: str = "general"
    supporting_evidence: list[str] = field(default_factory=list)
    confidence: float = 0.5
    priority: int = 5


@dataclass
class ConfidenceAssessment:
    overall: float = 0.0
    evidence_quality: float = 0.0
    citation_support: float = 0.0
    agreement_level: float = 0.0
    publication_diversity: float = 0.0
    retrieval_confidence: float = 0.0


@dataclass
class EvidenceRelationship:
    source_id: str
    target_id: str
    relationship_type: str = "related"
    strength: float = 0.5
    evidence: str = ""


@dataclass
class AnalysisStatistics:
    total_consensus: int = 0
    total_contradictions: int = 0
    total_trends: int = 0
    total_limitations: int = 0
    total_recommendations: int = 0
    total_relationships: int = 0
    overall_confidence: float = 0.0


@dataclass
class AnalysisValidationReport:
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unsupported_conclusions: list[str] = field(default_factory=list)
    weak_evidence: list[str] = field(default_factory=list)
    duplicate_insights: list[str] = field(default_factory=list)


@dataclass
class AnalysisMetadata:
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    duration_ms: float = 0.0
    model: str = ""
    validation_passed: bool = True
    validation_errors: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    sections: list[AnalysisSection] = field(default_factory=list)
    consensus: list[ConsensusResult] = field(default_factory=list)
    contradictions: list[Contradiction] = field(default_factory=list)
    trends: list[ResearchTrend] = field(default_factory=list)
    limitations: list[Limitation] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    confidence: ConfidenceAssessment = field(default_factory=ConfidenceAssessment)
    relationships: list[EvidenceRelationship] = field(default_factory=list)
    statistics: AnalysisStatistics = field(default_factory=AnalysisStatistics)
    metadata: AnalysisMetadata = field(default_factory=AnalysisMetadata)
    validation: AnalysisValidationReport | None = None
