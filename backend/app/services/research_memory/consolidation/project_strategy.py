from __future__ import annotations

from datetime import datetime, timezone

from app.core.logging import get_logger
from app.models.research_memory import LongTermMemoryCategory
from app.schemas.research_memory import LongTermMemoryCreate
from app.services.research_memory.consolidation.base import (
    ConsolidationConfig,
    ConsolidationResult,
)
from app.services.research_memory.manager import ResearchMemoryManager

logger = get_logger("services.research_memory.consolidation.project")


class ProjectConsolidationStrategy:
    """Consolidates project memories into long-term knowledge.

    Aggregates project memories grouped by category, extracting
    methodology preferences that persist across a project's lifecycle.
    """

    name: str = "project_consolidation"

    async def consolidate(
        self,
        manager: ResearchMemoryManager,
        config: ConsolidationConfig,
    ) -> ConsolidationResult:
        result = ConsolidationResult(strategy_name=self.name)

        if not config.project_id or not config.user_id:
            logger.info("project_id and user_id required for project consolidation")
            return result

        memories, total = await manager.list_project_memories(
            project_id=config.project_id,
            limit=config.max_memories_per_group,
        )
        result.source_count = len(memories)
        if not memories:
            return result

        already_ids = await self._existing_source_ids(manager, config)

        grouped: dict[str, list[dict]] = {}
        for m in memories:
            if str(m.id) in already_ids:
                continue
            cat = getattr(m, "category", None)
            cat_key = (
                cat.value if hasattr(cat, "value") else str(cat) if cat else "general"
            )
            grouped.setdefault(cat_key, []).append(
                {
                    "id": m.id,
                    "content": m.content,
                    "category": cat_key,
                    "confidence": m.confidence,
                }
            )

        if not grouped:
            logger.info("all project memories already consolidated")
            return result

        for cat_key, cat_memories in grouped.items():
            try:
                await self._consolidate_group(
                    manager, cat_key, cat_memories, config, result
                )
            except Exception as exc:
                result.errors.append(f"category '{cat_key}': {exc}")

        return result

    async def _existing_source_ids(
        self, manager: ResearchMemoryManager, config: ConsolidationConfig
    ) -> set[str]:
        existing: set[str] = set()
        ltms, total = await manager.list_long_term_memories(
            user_id=config.user_id,
            limit=config.max_memories_per_group * 10,
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
        category_key: str,
        memories: list[dict],
        config: ConsolidationConfig,
        result: ConsolidationResult,
    ) -> None:
        content = "\n\n".join(f"[{m['category']}] {m['content']}" for m in memories)
        source_ids = [str(m["id"]) for m in memories]
        max_conf = max(m["confidence"] for m in memories)

        if config.dry_run:
            result.skipped_count += 1
            return

        await manager.store_long_term_memory(
            LongTermMemoryCreate(
                user_id=config.user_id,
                category=LongTermMemoryCategory.METHODOLOGY_PREFERENCE,
                content=content,
                summary=f"Project consolidation ({category_key}: {len(memories)} memories)",
                source_session_ids=source_ids,
                importance=config.importance,
                confidence=max_conf,
                memory_metadata={
                    "consolidated_source_ids": source_ids,
                    "project_id": str(config.project_id),
                    "category": category_key,
                    "consolidated_at": datetime.now(timezone.utc).isoformat(),
                    "source_count": len(memories),
                    "strategy": self.name,
                },
            )
        )
        result.created_count += 1
