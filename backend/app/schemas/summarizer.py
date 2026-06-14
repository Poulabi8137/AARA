from __future__ import annotations

from pydantic import BaseModel, Field


class CitationRecord(BaseModel):
    claim: str
    supporting_chunk_ids: list[str] = Field(default_factory=list)
    source: str = ""


class Contradiction(BaseModel):
    topic: str
    statements: list[str] = Field(default_factory=list)
    source_chunk_ids: list[str] = Field(default_factory=list)
    severity: str = "medium"  # low, medium, high


class SectionSummary(BaseModel):
    subtopic: str
    executive_summary: str
    key_findings: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    important_statistics: list[str] = Field(default_factory=list)
    consensus_points: list[str] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    citations: list[CitationRecord] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=100.0)
    citation_count: int = 0
    source_count: int = 0

    coverage_score: float = Field(default=0.0, ge=0.0, le=100.0)
    evidence_density: float = Field(default=0.0, ge=0.0, le=100.0)
    citation_strength: float = Field(default=0.0, ge=0.0, le=100.0)
    consistency_score: float = Field(default=0.0, ge=0.0, le=100.0)
    summary_score: float = Field(default=0.0, ge=0.0, le=100.0)


class SummarizerMetrics(BaseModel):
    latency_seconds: float = 0.0
    bundles_processed: int = 0
    total_evidence_chunks: int = 0
    total_citations: int = 0
    total_contradictions: int = 0
    compression_ratio: float = 0.0
    evidence_utilization: float = 0.0
    average_summary_score: float = 0.0
    used_fallback: bool = False
    errors: list[str] = Field(default_factory=list)
