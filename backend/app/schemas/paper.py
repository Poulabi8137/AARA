from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProposalCreate(BaseModel):
    project_id: str
    gap_id: str | None = None
    domain: str = ""
    objective: str = ""
    keywords: str = ""
    methodology_preference: str = ""
    base_paper_doi: str | None = None
    base_paper_url: str | None = None


class ProposalResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    gap_id: str | None
    proposed_title: str
    problem_statement: str
    motivation: str
    research_questions: list[str]
    hypothesis: str
    objectives: list[str]
    expected_contributions: list[str]
    proposed_methodology: str
    evaluation_strategy: str
    future_scope: str
    keywords: list[str]
    domain: str | None
    base_paper_analysis: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BasePaperAnalysisCreate(BaseModel):
    project_id: str
    doi: str | None = None
    url: str | None = None


class BasePaperAnalysisResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    source_doi: str | None
    source_url: str | None
    source_filename: str | None
    abstract: str | None
    keywords: list[str] | None
    methodology: str | None
    dataset_description: str | None
    experiments: str | None
    limitations: str | None
    future_work: str | None
    references: list[str] | None
    originality_metadata: dict[str, Any] | None
    created_at: datetime

    class Config:
        from_attributes = True


class PaperGenerateRequest(BaseModel):
    project_id: str
    proposal_id: str


class PaperSectionResponse(BaseModel):
    id: uuid.UUID
    paper_id: uuid.UUID
    section_number: int
    section_title: str
    content: str
    word_count: int
    status: str
    evidence_classifications: dict[str, Any] | None

    class Config:
        from_attributes = True


class PaperCitationResponse(BaseModel):
    id: uuid.UUID
    paper_id: uuid.UUID
    citation_key: str
    authors: str | None
    title: str | None
    year: int | None
    journal: str | None
    doi: str | None
    url: str | None
    ieee_format: str | None
    verified: bool
    verification_errors: list[str] | None

    class Config:
        from_attributes = True


class PaperMetricsResponse(BaseModel):
    id: uuid.UUID
    paper_id: uuid.UUID
    novelty_score: float
    citation_coverage: float
    evidence_strength: float
    methodology_quality: float
    writing_quality: float
    logical_consistency: float
    academic_tone: float
    section_completeness: float
    composite_score: float
    details: dict[str, Any] | None
    suggestions: list[str] | None

    class Config:
        from_attributes = True


class PaperExportResponse(BaseModel):
    id: uuid.UUID
    paper_id: uuid.UUID
    format: str
    file_path: str | None
    generated_at: datetime

    class Config:
        from_attributes = True


class PaperResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    proposal_id: uuid.UUID | None
    title: str
    abstract: str
    keywords: list[str]
    authors: str
    status: str
    sections: list[PaperSectionResponse] = []
    citations: list[PaperCitationResponse] = []
    metrics: PaperMetricsResponse | None = None
    exports: list[PaperExportResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SectionRewriteRequest(BaseModel):
    operation: str = Field(description="rewrite, expand, condense, improve_tone, regenerate, add_citations, improve_depth")


class SectionRewriteResponse(BaseModel):
    section_id: uuid.UUID
    new_content: str
    revision_id: uuid.UUID
    operation: str


class QualityReviewResponse(BaseModel):
    novelty_score: float
    citation_coverage: float
    evidence_strength: float
    methodology_quality: float
    writing_quality: float
    logical_consistency: float
    academic_tone: float
    section_completeness: float
    composite_score: float
    suggestions: list[str]
    strengths: list[str]
    weaknesses: list[str]


class CitationValidationResponse(BaseModel):
    citations: list[dict[str, Any]]
    total: int
    duplicates: list[str]
    verified_count: int
    has_issues: bool


class EvidenceValidationResponse(BaseModel):
    sections: list[dict[str, Any]]
    coverage: dict[str, int]
    overall_supported_ratio: float
    status: str


class PaperListResponse(BaseModel):
    papers: list[PaperResponse]
    total: int
