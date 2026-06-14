from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.agents.state import ResearchState
from app.llm.provider import LLMProvider
from app.core.logging import get_logger

logger = get_logger("agents.base")


@dataclass
class AgentResult:
    """Standardised result envelope from any agent execution."""
    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base for all research agents.

    Lifecycle: validate_input -> run -> validate_output -> log_execution.
    Subclasses override arun() and optionally the lifecycle hooks.
    """

    agent_name: str = ""
    description: str = ""
    requires_human_approval: bool = False

    def __init__(self, llm_provider: LLMProvider) -> None:
        self.llm = llm_provider

    # ── Abstract ──────────────────────────────────────────

    @abstractmethod
    async def arun(self, state: ResearchState) -> ResearchState:
        """Core execution logic. Subclasses implement this."""
        ...

    # ── Lifecycle hooks ───────────────────────────────────

    async def validate_input(self, state: ResearchState) -> None:
        """Raise ValueError if preconditions are not met."""
        if not state.get("query", "").strip():
            raise ValueError("query must not be empty")

    async def validate_output(self, state: ResearchState) -> None:
        """Override to assert postconditions after arun()."""

    async def log_execution(self, state: ResearchState, start: datetime) -> None:
        """Log execution telemetry."""
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        logger.info(
            "agent execution complete",
            extra={
                "agent": self.agent_name,
                "duration_seconds": elapsed,
                "status": state.get("status"),
            },
        )

    async def handle_error(self, state: ResearchState, exc: Exception) -> ResearchState:
        """Graceful error recovery. Override for custom fallback logic."""
        errors = state.get("errors", [])
        errors.append(f"[{self.agent_name}] {exc}")
        state["errors"] = errors
        state["status"] = "failed"
        return state

    # ── Public execution entry point ──────────────────────

    async def run(self, state: ResearchState) -> AgentResult:
        """Full lifecycle entry point called by graph nodes."""
        start = datetime.now(timezone.utc)
        state["timestamp"] = start.isoformat()
        state["status"] = "running"

        try:
            await self.validate_input(state)
            state = await self.arun(state)
            await self.validate_output(state)
        except Exception as exc:
            state = await self.handle_error(state, exc)
            await self.log_execution(state, start)
            return AgentResult(success=False, error=str(exc), metadata={"agent": self.agent_name})

        # Preserve agent-specific status (e.g. "planner_complete") if already set
        if state.get("status") in ("running", None):
            state["status"] = "completed"
        await self.log_execution(state, start)
        return AgentResult(success=True, metadata={"agent": self.agent_name})
