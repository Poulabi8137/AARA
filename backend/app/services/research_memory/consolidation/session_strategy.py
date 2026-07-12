from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.schemas.research_memory import LongTermMemoryCreate
from app.services.research_memory.consolidation.base import (
    ConsolidationConfig,
    ConsolidationResult,
)
from app.services.research_memory.manager import ResearchMemoryManager

logger = get_logger("services.research_memory.consolidation.session")


class SessionConsolidationStrategy:
    """Consolidates session memories into long-term memory.

    Groups unconsolidated session memories by session_id, deduplicates
    by content hash, and creates a consolidated ``CROSS_SESSION_INSIGHT``
    long-term memory entry.
    """

    name: str = "session_consolidation"

    async def consolidate(
        self,
        manager: ResearchMemoryManager,
        config: ConsolidationConfig,
    ) -> ConsolidationResult:
        result = ConsolidationResult(strategy_name=self.name)

        if not config.user_id:
            logger.info("no user_id provided, skipping session consolidation")
            return result

        raw_memories, total = await manager.list_session_memories_by_user(
            user_id=config.user_id,
            limit=config.max_memories_per_group,
        )
        result.source_count = len(raw_memories)
        if not raw_memories:
            return result

        already_ids = await self._existing_source_ids(manager, config)
        groups: dict[uuid.UUID, list[dict]] = {}

        for mem in raw_memories:
            if str(mem.id) in already_ids:
                continue
            groups.setdefault(mem.session_id, []).append({
                "id": mem.id,
                "content": mem.content,
                "memory_type": mem.memory_type.value if hasattr(mem, "memory_type") else "unknown",
                "confidence": mem.confidence,
            })

        if not groups:
            logger.info("all session memories already consolidated")
            return result

        for session_id, memories in groups.items():
            try:
                await self._consolidate_group(manager, session_id, memories, config, result)
            except Exception as exc:
                result.errors.append(f"session {session_id}: {exc}")

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
        session_id: uuid.UUID,
        memories: list[dict],
        config: ConsolidationConfig,
        result: ConsolidationResult,
    ) -> None:
        seen: set[str] = set()
        unique = []
        for m in memories:
            h = hashlib.sha256(m["content"].encode()).hexdigest()[:64]
            if h not in seen:
                seen.add(h)
                unique.append(m)

        result.merged_count += len(memories) - len(unique)

        if len(unique) < 1:
            result.skipped_count += 1
            return

        content = "\n\n".join(
            f"[{m['memory_type']}] {m['content']}" for m in unique
        )
        source_ids = [str(m["id"]) for m in unique]
        max_conf = max(m["confidence"] for m in unique)

        if config.dry_run:
            result.skipped_count += 1
            return

        await manager.store_long_term_memory(LongTermMemoryCreate(
            user_id=config.user_id,
            category=config.target_category,
            content=content,
            summary=f"Session consolidation ({len(unique)} memories from session {session_id})",
            source_session_ids=source_ids,
            importance=config.importance,
            confidence=max_conf,
            memory_metadata={
                "consolidated_source_ids": source_ids,
                "session_id": str(session_id),
                "consolidated_at": datetime.now(timezone.utc).isoformat(),
                "source_count": len(unique),
                "strategy": self.name,
            },
        ))
        result.created_count += 1
