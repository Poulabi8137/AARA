from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.models.research_memory import LongTermMemoryCategory, MemoryImportance
from app.schemas.research_memory import LongTermMemoryCreate
from app.services.research_memory.consolidation.base import (
    ConsolidationConfig,
    ConsolidationResult,
)
from app.services.research_memory.manager import ResearchMemoryManager

logger = get_logger("services.research_memory.consolidation.paper")


class PaperConsolidationStrategy:
    """Consolidates paper memories into long-term knowledge.

    Groups related paper memories by project and synthesises
    reusable findings into ``REUSABLE_FINDING`` long-term entries.
    """

    name: str = "paper_consolidation"

    async def consolidate(
        self,
        manager: ResearchMemoryManager,
        config: ConsolidationConfig,
    ) -> ConsolidationResult:
        result = ConsolidationResult(strategy_name=self.name)

        if not config.project_id:
            logger.info("no project_id provided, skipping paper consolidation")
            return result

        papers, total = await manager.list_paper_memories(
            project_id=config.project_id,
            limit=config.max_memories_per_group,
        )
        result.source_count = len(papers)
        if not papers:
            return result

        user_id = papers[0].user_id or config.user_id

        already_ids = await self._existing_source_ids(manager, user_id)

        grouped: dict[str, list[dict]] = {}
        for p in papers:
            if str(p.id) in already_ids:
                continue
            key = str(p.project_id) if hasattr(p, "project_id") and p.project_id else "default"
            grouped.setdefault(key, []).append({
                "id": p.id,
                "content": p.content,
                "title": getattr(p, "title", ""),
                "user_id": getattr(p, "user_id", user_id),
                "confidence": p.confidence,
            })

        if not grouped:
            logger.info("all paper memories already consolidated")
            return result

        for project_key, memories in grouped.items():
            try:
                await self._consolidate_group(manager, uuid.UUID(project_key) if project_key != "default" else config.project_id, memories, config, result)
            except Exception as exc:
                result.errors.append(f"paper group {project_key}: {exc}")

        return result

    async def _existing_source_ids(
        self, manager: ResearchMemoryManager, user_id: uuid.UUID | None
    ) -> set[str]:
        existing: set[str] = set()
        if not user_id:
            return existing
        ltms, total = await manager.list_long_term_memories(
            user_id=user_id,
            limit=1000,
        )
        for ltm in ltms:
            meta = ltm.memory_metadata or {}
            ids = meta.get("consolidated_source_ids", [])
            if isinstance(ids, list):
                existing.update(ids)
        return existing

    async def _consolidate_group(
        self,
        manager: ResearchMemoryManager,
        project_id: uuid.UUID,
        memories: list[dict],
        config: ConsolidationConfig,
        result: ConsolidationResult,
    ) -> None:
        content = "\n\n".join(
            f"[{m['title']}] {m['content']}" for m in memories
        )
        source_ids = [str(m["id"]) for m in memories]
        max_conf = max(m["confidence"] for m in memories)
        effective_user_id = next((m["user_id"] for m in memories if m.get("user_id")), config.user_id)

        if config.dry_run:
            result.skipped_count += 1
            return

        await manager.store_long_term_memory(LongTermMemoryCreate(
            user_id=effective_user_id,
            category=LongTermMemoryCategory.REUSABLE_FINDING,
            content=content,
            summary=f"Paper consolidation ({len(memories)} papers from project {project_id})",
            source_session_ids=source_ids,
            importance=MemoryImportance.HIGH,
            confidence=max_conf,
            memory_metadata={
                "consolidated_source_ids": source_ids,
                "project_id": str(project_id),
                "consolidated_at": datetime.now(timezone.utc).isoformat(),
                "source_count": len(memories),
                "strategy": self.name,
            },
        ))
        result.created_count += 1
