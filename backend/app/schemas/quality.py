from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

QualityCapability = Literal[
    "plagiarism", "ai_detection", "publication_readiness", "submission_assistant"
]


class QualityCheckRequest(BaseModel):
    text: str = Field(..., min_length=1)
    document_id: str | None = None


class QualityCheckResponse(BaseModel):
    status: str
    capability: str
    message: str
