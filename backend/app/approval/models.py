from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class CheckpointStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    REVISION_REQUESTED = "revision_requested"


class ApprovalDecision(enum.StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REVISE = "revise"
    CONTINUE = "continue"


@dataclass
class ApprovalCheckpoint:
    id: str
    workflow_id: str
    phase: str
    status: CheckpointStatus = CheckpointStatus.PENDING
    input_summary: str = ""
    output_snapshot: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    expires_at: datetime | None = None
    decided_at: datetime | None = None
    decision: str | None = None
    notes: str = ""
