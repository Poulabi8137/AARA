from __future__ import annotations

import abc
from typing import Any

from app.agents.lifecycle import AgentLifecycleManager
from app.agents.models import AgentContext, AgentOutput, AgentPhase, AgentState, AgentStatus


class BaseAgent(abc.ABC):
    agent_id: str = ""
    agent_name: str = ""
    version: str = "1.0"
    max_retries: int = 3
    timeout_seconds: int = 60

    def __init__(self) -> None:
        self._state = AgentState(
            agent_id=self.agent_id,
            workflow_id="",
            status=AgentStatus.INITIALIZED,
            current_phase=AgentPhase.IDLE,
            max_retries=self.max_retries,
        )
        self._lifecycle = AgentLifecycleManager(self._state)

    @abc.abstractmethod
    async def execute(self, context: AgentContext) -> AgentOutput:
        ...

    async def validate_output(self, output: AgentOutput) -> bool:
        _ = output
        return True

    async def lifecycle(self) -> AgentState:
        return self._state

    async def update_state(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)

    async def handle_error(self, error: Exception, context: AgentContext) -> AgentOutput:
        self._state.retry_count += 1
        if self._state.retry_count < self.max_retries:
            self._state.status = AgentStatus.ERROR
            self._state.current_phase = AgentPhase.IDLE
            raise error
        return AgentOutput(
            agent_id=self.agent_id,
            workflow_id=context.workflow_id,
            output={"error": str(error)},
            summary=f"Agent failed after {self._state.retry_count} retries: {error}",
            duration_ms=0,
        )

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return len(text) // 4
