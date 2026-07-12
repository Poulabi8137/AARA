from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from app.models.research_memory import LongTermMemoryCategory, MemoryImportance


@dataclass
class ConsolidationConfig:
    """Per-run configuration for a consolidation strategy."""

    user_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    min_confidence: float = 0.3
    max_memories_per_group: int = 50
    similarity_threshold: float = 0.85
    target_category: LongTermMemoryCategory = LongTermMemoryCategory.CROSS_SESSION_INSIGHT
    importance: MemoryImportance = MemoryImportance.MEDIUM
    batch_size: int = 100
    dry_run: bool = False


@dataclass
class ConsolidationResult:
    """Outcome of a single consolidation run."""

    strategy_name: str
    source_count: int = 0
    created_count: int = 0
    skipped_count: int = 0
    merged_count: int = 0
    archived_count: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@runtime_checkable
class ConsolidationStrategy(Protocol):
    """Interface that every consolidation strategy must implement.

    Strategies are stateless by design — all configuration comes via
    ``ConsolidationConfig`` and all persistence goes through the
    ``ResearchMemoryManager``.  This makes them easy to test, compose,
    and swap at runtime.
    """

    name: str

    async def consolidate(
        self,
        manager: object,
        config: ConsolidationConfig,
    ) -> ConsolidationResult:
        ...
