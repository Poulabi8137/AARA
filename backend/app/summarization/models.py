from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from app.rag.models import RetrievedEvidence


class SummaryLevel(str, Enum):
    BRIEF = "brief"
    STANDARD = "standard"
    DETAILED = "detailed"
    LITERATURE_REVIEW = "literature_review"
    EXECUTIVE_SUMMARY = "executive_summary"


class SectionType(str, Enum):
    ABSTRACT = "abstract"
    BACKGROUND = "background"
    PROBLEM_STATEMENT = "problem_statement"
    METHODOLOGY = "methodology"
    EXPERIMENTAL_SETUP = "experimental_setup"
    RESULTS = "results"
    DISCUSSION = "discussion"
    LIMITATIONS = "limitations"
    FUTURE_WORK = "future_work"
    CONCLUSION = "conclusion"


class GroupingStrategy(str, Enum):
    TOPIC = "topic"
    METHODOLOGY = "methodology"
    YEAR = "year"
    DATASET = "dataset"
    BENCHMARK = "benchmark"
    AUTHOR = "author"
    INSTITUTION = "institution"
    DOMAIN = "domain"


class CitationMode(str, Enum):
    INLINE = "inline"
    FOOTNOTE = "footnote"
    ENDNOTE = "endnote"
    NONE = "none"


@dataclass
class SummaryRequest:
    query: str
    evidence: list[RetrievedEvidence] | None = None
    level: SummaryLevel = SummaryLevel.STANDARD
    sections: list[SectionType] | None = None
    grouping: GroupingStrategy = GroupingStrategy.TOPIC
    citation_mode: CitationMode = CitationMode.INLINE
    max_length: int = 4096
    user_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None


@dataclass
class SummaryChunk:
    content: str
    section: SectionType
    citations: list[str] = field(default_factory=list)
    confidence: float = 1.0
    source_ids: list[str] = field(default_factory=list)


@dataclass
class SummarySection:
    type: SectionType
    title: str
    content: str
    chunks: list[SummaryChunk] = field(default_factory=list)
    evidence_count: int = 0
    citations: list[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class EvidenceGroup:
    label: str
    evidence: list[RetrievedEvidence] = field(default_factory=list)
    citation_keys: list[str] = field(default_factory=list)
    key_points: list[str] = field(default_factory=list)


@dataclass
class ExtractedFinding:
    finding: str
    supporting_evidence: list[str] = field(default_factory=list)
    confidence: float = 0.5
    citations: list[str] = field(default_factory=list)
    category: str = "general"


@dataclass
class ResearchGap:
    gap: str
    evidence: list[str] = field(default_factory=list)
    gap_type: str = "unanswered_question"
    confidence: float = 0.5


@dataclass
class SummaryStatistics:
    total_sources: int = 0
    total_citations: int = 0
    total_sections: int = 0
    total_findings: int = 0
    total_gaps: int = 0
    total_tokens: int = 0
    evidence_by_type: dict[str, int] = field(default_factory=dict)


@dataclass
class SummaryMetadata:
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    duration_ms: float = 0.0
    level: SummaryLevel = SummaryLevel.STANDARD
    model: str = ""
    validation_passed: bool = True
    validation_errors: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_citations: list[str] = field(default_factory=list)
    unsupported_claims: list[str] = field(default_factory=list)
    missing_sections: list[str] = field(default_factory=list)


@dataclass
class SummaryResult:
    summary: str
    sections: list[SummarySection] = field(default_factory=list)
    findings: list[ExtractedFinding] = field(default_factory=list)
    gaps: list[ResearchGap] = field(default_factory=list)
    groups: list[EvidenceGroup] = field(default_factory=list)
    statistics: SummaryStatistics = field(default_factory=SummaryStatistics)
    metadata: SummaryMetadata = field(default_factory=SummaryMetadata)
    validation: ValidationReport | None = None
