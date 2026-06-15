from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ExportFormat(str, Enum):
    markdown = "markdown"
    json = "json"
    pdf = "pdf"
    docx = "docx"
    html = "html"


class ReportCitation(BaseModel):
    claim: str
    source: str = ""
    supporting_chunk_ids: list[str] = Field(default_factory=list)
    subtopic: str = ""


class ReportContradiction(BaseModel):
    topic: str
    statements: list[str] = Field(default_factory=list)
    subtopic: str = ""
    severity: str = "medium"


class ReportSection(BaseModel):
    title: str
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    evidence_highlights: list[str] = Field(default_factory=list)
    statistics: list[str] = Field(default_factory=list)
    contradictions: list[ReportContradiction] = Field(default_factory=list)
    citations: list[ReportCitation] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=100.0)
    citation_count: int = 0
    source_count: int = 0


class ReportReference(BaseModel):
    reference_id: str
    source: str
    claims: list[str] = Field(default_factory=list)
    subtopics: list[str] = Field(default_factory=list)
    occurrence_count: int = 1


class ReportMetrics(BaseModel):
    report_completeness: float = Field(default=0.0, ge=0.0, le=100.0)
    evidence_strength: float = Field(default=0.0, ge=0.0, le=100.0)
    citation_strength: float = Field(default=0.0, ge=0.0, le=100.0)
    coverage_score: float = Field(default=0.0, ge=0.0, le=100.0)
    research_quality_score: float = Field(default=0.0, ge=0.0, le=100.0)
    section_count: int = 0
    reference_count: int = 0
    citation_count: int = 0
    report_length: int = 0
    generation_latency: float = 0.0


class ResearchReport(BaseModel):
    title: str
    query: str
    executive_summary: str
    introduction: str
    research_objectives: list[str] = Field(default_factory=list)
    methodology: str
    sections: list[ReportSection] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    contradictions: list[ReportContradiction] = Field(default_factory=list)
    research_gaps: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    future_research: list[str] = Field(default_factory=list)
    conclusion: str
    references: list[ReportReference] = Field(default_factory=list)
    metrics: ReportMetrics = Field(default_factory=ReportMetrics)
    generated_at: str = ""

    # Formatted outputs
    markdown: str = ""
    report_json: str = ""


class ReportGenerateRequest(BaseModel):
    planner_output: str | None = None
    summaries: list[dict[str, Any]] = Field(default_factory=list)
    research_gaps: list[dict[str, Any]] = Field(default_factory=list)
    query: str = ""
    objective: str = ""
    format: ExportFormat = ExportFormat.markdown


class ReportExportRequest(BaseModel):
    report: ResearchReport
    format: ExportFormat = ExportFormat.markdown
