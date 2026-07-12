from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.logging import get_logger
from app.models.research_memory import MemoryImportance
from app.schemas.research_memory import LongTermMemoryUpdate
from app.services.research_memory.consolidation.base import (
    ConsolidationConfig,
    ConsolidationResult,
)
from app.services.research_memory.manager import ResearchMemoryManager

logger = get_logger("services.research_memory.consolidation.aging")


class MemoryAgingEngine:
    """Applies aging rules to long-term memories.

    - Stale memories (beyond TTL) have their confidence decayed.
    - Memories below the archive threshold are archived.
    """

    name: str = "memory_aging"

    def __init__(
        self,
        active_ttl: timedelta = timedelta(days=90),
        low_importance_ttl: timedelta = timedelta(days=180),
        archive_ttl: timedelta = timedelta(days=365),
        decay_factor: float = 0.05,
        archive_threshold: float = 0.2,
    ) -> None:
        self._active_ttl = active_ttl
        self._low_importance_ttl = low_importance_ttl
        self._archive_ttl = archive_ttl
        self._decay_factor = decay_factor
        self._archive_threshold = archive_threshold

    async def age(
        self,
        manager: ResearchMemoryManager,
        config: ConsolidationConfig,
    ) -> ConsolidationResult:
        result = ConsolidationResult(strategy_name=self.name)

        if not config.user_id:
            logger.info("no user_id provided, skipping aging")
            return result

        ltms, total = await manager.list_long_term_memories(
            user_id=config.user_id,
            limit=config.max_memories_per_group,
        )
        result.source_count = len(ltms)
        if not ltms:
            return result

        now = datetime.now(timezone.utc)

        for ltm in ltms:
            meta = (
                (ltm.memory_metadata or {}) if hasattr(ltm, "memory_metadata") else {}
            )
            if meta.get("archived"):
                continue

            created = getattr(ltm, "created_at", now)
            age = now - created
            importance = getattr(ltm, "importance", MemoryImportance.MEDIUM)
            current_confidence = getattr(ltm, "confidence", 0.0)

            ttl = (
                self._active_ttl
                if importance != MemoryImportance.LOW
                else self._low_importance_ttl
            )
            if age < ttl:
                continue

            if config.dry_run:
                result.skipped_count += 1
                continue

            overdue = (age - ttl).days / max(ttl.days, 1)
            decay = self._decay_factor * max(1.0, overdue)
            new_confidence = max(0.0, current_confidence - decay)

            if new_confidence <= self._archive_threshold or age >= self._archive_ttl:
                await manager.update_long_term_memory(
                    memory_id=ltm.id,
                    data=LongTermMemoryUpdate(
                        importance=MemoryImportance.LOW,
                        confidence=new_confidence,
                        memory_metadata={
                            **meta,
                            "archived": True,
                            "archived_at": now.isoformat(),
                            "archive_reason": f"age={age.days}d, confidence={new_confidence:.2f}",
                        },
                    ),
                )
                result.archived_count += 1
            else:
                await manager.update_long_term_memory(
                    memory_id=ltm.id,
                    data=LongTermMemoryUpdate(
                        confidence=new_confidence,
                        memory_metadata={
                            **meta,
                            "last_decayed_at": now.isoformat(),
                            "decay_amount": decay,
                        },
                    ),
                )
                result.merged_count += 1

        return result
