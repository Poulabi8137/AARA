from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class PlannerOutput(BaseModel):
    """Structured research plan produced by the PlannerAgent.

    Every downstream agent (retrieval, summarizer, gap-detection,
    report-generator) reads from this schema.
    """

    research_goal: str = Field(
        ..., min_length=10, description="Single-sentence research objective"
    )
    research_questions: list[str] = Field(
        ..., min_length=3, description="Minimum 3 research questions"
    )
    keywords: list[str] = Field(
        ..., min_length=3, description="Core keywords for search"
    )
    search_queries: list[str] = Field(
        ..., min_length=5, description="Search queries for retrieval phase"
    )
    subtopics: list[str] = Field(
        ..., min_length=3, description="Sub-areas to investigate"
    )
    methodology: str = Field(
        default="literature review", description="Research methodology"
    )
    expected_deliverables: list[str] = Field(
        ..., min_length=1, description="Tangible outputs"
    )
    priority_areas: list[str] = Field(
        ..., min_length=1, description="High-priority focus zones"
    )
    risk_areas: list[str] = Field(
        ..., min_length=0, description="Potential risks or gaps"
    )
    estimated_steps: int = Field(
        default=5, ge=1, le=20, description="Estimated workflow steps"
    )

    planning_score: int = Field(
        default=0, ge=0, le=100, description="Overall plan quality 0-100"
    )
    completeness: int = Field(default=0, ge=0, le=100, description="Completeness score")
    coverage: int = Field(default=0, ge=0, le=100, description="Breadth of coverage")
    specificity: int = Field(default=0, ge=0, le=100, description="Level of detail")

    @field_validator("research_questions")
    @classmethod
    def no_duplicate_questions(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for q in v:
            qs = q.strip().lower()
            if qs not in seen:
                seen.add(qs)
                result.append(q.strip())
        if len(result) < 3:
            raise ValueError("Need at least 3 unique research questions after dedup")
        return result

    @field_validator("search_queries")
    @classmethod
    def no_duplicate_queries(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for q in v:
            qs = q.strip().lower()
            if qs not in seen:
                seen.add(qs)
                result.append(q.strip())
        if len(result) < 5:
            raise ValueError("Need at least 5 unique search queries after dedup")
        return result

    @field_validator("subtopics")
    @classmethod
    def no_duplicate_subtopics(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for t in v:
            ts = t.strip().lower()
            if ts not in seen:
                seen.add(ts)
                result.append(t.strip())
        if len(result) < 3:
            raise ValueError("Need at least 3 unique subtopics after dedup")
        return result


class PlannerMetrics(BaseModel):
    latency_seconds: float = 0.0
    token_usage: dict[str, int] = {}
    validation_failures: int = 0
    repair_attempts: int = 0
    used_fallback: bool = False
