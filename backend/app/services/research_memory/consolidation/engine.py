from __future__ import annotations

import time

from app.core.logging import get_logger
from app.services.research_memory.consolidation.aging import MemoryAgingEngine
from app.services.research_memory.consolidation.base import (
    ConsolidationConfig,
    ConsolidationResult,
)
from app.services.research_memory.consolidation.evolution import KnowledgeEvolution
from app.services.research_memory.consolidation.paper_strategy import (
    PaperConsolidationStrategy,
)
from app.services.research_memory.consolidation.project_strategy import (
    ProjectConsolidationStrategy,
)
from app.services.research_memory.consolidation.session_strategy import (
    SessionConsolidationStrategy,
)
from app.services.research_memory.manager import ResearchMemoryManager

logger = get_logger("services.research_memory.consolidation.engine")


class ConsolidationEngine:
    """Top-level orchestrator for memory consolidation.

    Owns a set of ``ConsolidationStrategy`` instances and runs them
    in the prescribed order over the given ``ResearchMemoryManager``.

    Default execution order:
      1. **Knowledge evolution** — reinforce existing LTM with new evidence.
      2. **Session consolidation** — session memories → LTM.
      3. **Paper consolidation** — paper memories → LTM.
      4. **Project consolidation** — project memories → LTM.
      5. **Memory aging** — decay/archive stale LTM.
    """

    def __init__(
        self,
        manager: ResearchMemoryManager,
        *,
        session_strategy: SessionConsolidationStrategy | None = None,
        paper_strategy: PaperConsolidationStrategy | None = None,
        project_strategy: ProjectConsolidationStrategy | None = None,
        evolution: KnowledgeEvolution | None = None,
        aging: MemoryAgingEngine | None = None,
    ) -> None:
        self._manager = manager
        self._session_strategy = session_strategy or SessionConsolidationStrategy()
        self._paper_strategy = paper_strategy or PaperConsolidationStrategy()
        self._project_strategy = project_strategy or ProjectConsolidationStrategy()
        self._evolution = evolution or KnowledgeEvolution()
        self._aging = aging or MemoryAgingEngine()

    async def consolidate_session(
        self,
        config: ConsolidationConfig | None = None,
    ) -> ConsolidationResult:
        cfg = config or ConsolidationConfig()
        start = time.monotonic()
        result = await self._session_strategy.consolidate(self._manager, cfg)
        result.duration_seconds = time.monotonic() - start
        logger.info(
            "session consolidation finished",
            extra={
                "created": result.created_count,
                "skipped": result.skipped_count,
                "duration": result.duration_seconds,
            },
        )
        return result

    async def consolidate_paper(
        self,
        config: ConsolidationConfig | None = None,
    ) -> ConsolidationResult:
        cfg = config or ConsolidationConfig()
        start = time.monotonic()
        result = await self._paper_strategy.consolidate(self._manager, cfg)
        result.duration_seconds = time.monotonic() - start
        logger.info(
            "paper consolidation finished",
            extra={
                "created": result.created_count,
                "skipped": result.skipped_count,
                "duration": result.duration_seconds,
            },
        )
        return result

    async def consolidate_project(
        self,
        config: ConsolidationConfig | None = None,
    ) -> ConsolidationResult:
        cfg = config or ConsolidationConfig()
        start = time.monotonic()
        result = await self._project_strategy.consolidate(self._manager, cfg)
        result.duration_seconds = time.monotonic() - start
        logger.info(
            "project consolidation finished",
            extra={
                "created": result.created_count,
                "skipped": result.skipped_count,
                "duration": result.duration_seconds,
            },
        )
        return result

    async def evolve(
        self,
        config: ConsolidationConfig | None = None,
    ) -> ConsolidationResult:
        cfg = config or ConsolidationConfig()
        start = time.monotonic()
        result = await self._evolution.evolve(self._manager, cfg)
        result.duration_seconds = time.monotonic() - start
        return result

    async def age(
        self,
        config: ConsolidationConfig | None = None,
    ) -> ConsolidationResult:
        cfg = config or ConsolidationConfig()
        start = time.monotonic()
        result = await self._aging.age(self._manager, cfg)
        result.duration_seconds = time.monotonic() - start
        return result

    async def consolidate_all(
        self,
        config: ConsolidationConfig | None = None,
    ) -> dict[str, ConsolidationResult]:
        """Run every strategy in the default order.

        Returns a mapping of strategy name → result.
        """
        cfg = config or ConsolidationConfig()
        results: dict[str, ConsolidationResult] = {}

        results["evolution"] = await self.evolve(cfg)
        results["session"] = await self.consolidate_session(cfg)
        results["paper"] = await self.consolidate_paper(cfg)
        results["project"] = await self.consolidate_project(cfg)
        results["aging"] = await self.age(cfg)

        total_created = sum(r.created_count for r in results.values())
        total_archived = sum(r.archived_count for r in results.values())
        total_errors = sum(len(r.errors) for r in results.values())
        logger.info(
            "full consolidation cycle complete",
            extra={
                "created": total_created,
                "archived": total_archived,
                "errors": total_errors,
            },
        )
        return results
