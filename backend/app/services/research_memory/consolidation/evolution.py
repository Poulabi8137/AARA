from __future__ import annotations

from datetime import datetime, timezone

from app.core.logging import get_logger
from app.models.research_memory import MemoryImportance
from app.schemas.research_memory import LongTermMemoryUpdate
from app.services.research_memory.consolidation.base import (
    ConsolidationConfig,
    ConsolidationResult,
)
from app.services.research_memory.manager import ResearchMemoryManager

logger = get_logger("services.research_memory.consolidation.evolution")


class KnowledgeEvolution:
    """Reinforces long-term memories when new supporting evidence appears.

    Searches for related existing LTM entries and boosts their confidence
    when related session/paper/project memories are found above the
    propagation threshold.
    """

    name: str = "knowledge_evolution"

    async def evolve(
        self,
        manager: ResearchMemoryManager,
        config: ConsolidationConfig,
    ) -> ConsolidationResult:
        result = ConsolidationResult(strategy_name=self.name)

        if not config.user_id:
            logger.info("no user_id provided, skipping evolution")
            return result

        ltms, total = await manager.list_long_term_memories(
            user_id=config.user_id,
            limit=config.max_memories_per_group,
        )
        result.source_count = len(ltms)
        if not ltms:
            return result

        evolved = 0
        for ltm in ltms:
            try:
                if await self._evolve_one(manager, ltm, config):
                    evolved += 1
            except Exception as exc:
                result.errors.append(f"LTM {ltm.id}: {exc}")

        result.merged_count = evolved
        return result

    async def _evolve_one(
        self,
        manager: ResearchMemoryManager,
        ltm: object,
        config: ConsolidationConfig,
    ) -> bool:
        meta = (ltm.memory_metadata or {}) if hasattr(ltm, "memory_metadata") else {}
        if meta.get("archived"):
            return False

        content = getattr(ltm, "content", "")
        if not content:
            return False

        result = await manager.search(
            query=content[:500],
            user_id=config.user_id,
            top_k=5,
        )

        strong = [h for h in result.results if hasattr(h, "score") and h.score >= 0.85]
        if not strong:
            return False

        current_confidence = getattr(ltm, "confidence", 0.0)
        current_importance = getattr(ltm, "importance", MemoryImportance.MEDIUM)
        boost = 0.1 * len(strong)
        new_confidence = min(1.0, current_confidence + boost)

        new_importance = current_importance
        if new_confidence >= 0.85 and current_importance == MemoryImportance.HIGH:
            new_importance = MemoryImportance.CRITICAL
        elif new_confidence >= 0.6 and current_importance == MemoryImportance.MEDIUM:
            new_importance = MemoryImportance.HIGH

        if config.dry_run:
            return False

        await manager.update_long_term_memory(
            memory_id=ltm.id,
            data=LongTermMemoryUpdate(
                importance=new_importance
                if new_importance != current_importance
                else None,
                confidence=new_confidence
                if new_confidence != current_confidence
                else None,
                memory_metadata={
                    **meta,
                    "last_evolved_at": datetime.now(timezone.utc).isoformat(),
                    "evolution_count": meta.get("evolution_count", 0) + 1,
                    "supporting_hits": len(strong),
                },
            ),
        )
        return True
