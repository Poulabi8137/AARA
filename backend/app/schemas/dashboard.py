from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    status: str
    current_phase: str | None = None
    current_agent: str | None = None
    progress_pct: float
    started_at: datetime | None = None
    completed_at: datetime | None = None
    elapsed_seconds: float


class TokenUsageResponse(BaseModel):
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    estimated_cost: float


class ProviderUsageResponse(BaseModel):
    provider: str
    model: str
    calls: int
    tokens: int
    cost: float


class EvaluationScoreResponse(BaseModel):
    metric: str
    score: float
    details: dict | None = None


class DashboardResponse(BaseModel):
    workflow: WorkflowStatusResponse
    tokens: TokenUsageResponse
    providers: list[ProviderUsageResponse]
    evaluation_scores: list[EvaluationScoreResponse]
    timeline: list[dict]
