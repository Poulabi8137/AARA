from __future__ import annotations

from datetime import UTC, datetime

from app.agents.models import AgentPhase, AgentState, AgentStatus


class AgentLifecycleManager:
    _PHASE_TO_STATUS: dict[AgentPhase, AgentStatus] = {
        AgentPhase.IDLE: AgentStatus.INITIALIZED,
        AgentPhase.PLANNING: AgentStatus.PLANNING,
        AgentPhase.REASONING: AgentStatus.REASONING,
        AgentPhase.TOOL_USE: AgentStatus.EXECUTING_TOOL,
        AgentPhase.REFLECTING: AgentStatus.REFLECTING,
        AgentPhase.VALIDATING: AgentStatus.SELF_VALIDATING,
        AgentPhase.OUTPUTTING: AgentStatus.OUTPUTTING_RESULT,
    }

    _ALLOWED_TRANSITIONS: dict[AgentPhase, set[AgentPhase]] = {
        AgentPhase.IDLE: {AgentPhase.PLANNING},
        AgentPhase.PLANNING: {AgentPhase.REASONING},
        AgentPhase.REASONING: {AgentPhase.TOOL_USE},
        AgentPhase.TOOL_USE: {AgentPhase.REFLECTING},
        AgentPhase.REFLECTING: {AgentPhase.PLANNING, AgentPhase.VALIDATING},
        AgentPhase.VALIDATING: {AgentPhase.OUTPUTTING, AgentPhase.PLANNING},
        AgentPhase.OUTPUTTING: set(),
    }

    def __init__(self, state: AgentState) -> None:
        self._state = state

    def transition(self, new_phase: AgentPhase) -> None:
        if not self.can_transition_to(new_phase):
            raise InvalidTransitionError(
                f"Cannot transition from {self._state.current_phase.value} to {new_phase.value}"
            )
        if new_phase == AgentPhase.PLANNING and self._state.current_phase == AgentPhase.IDLE:
            self._state.started_at = datetime.now(UTC)
        if new_phase == AgentPhase.PLANNING and self._state.current_phase in (
            AgentPhase.REFLECTING, AgentPhase.VALIDATING
        ):
            pass
        self._state.current_step_started_at = datetime.now(UTC)
        self._state.current_phase = new_phase
        self._state.status = self._PHASE_TO_STATUS.get(new_phase, AgentStatus.INITIALIZED)

    def get_allowed_transitions(self) -> list[AgentPhase]:
        return list(self._ALLOWED_TRANSITIONS.get(self._state.current_phase, set()))

    def can_transition_to(self, target: AgentPhase) -> bool:
        allowed = self._ALLOWED_TRANSITIONS.get(self._state.current_phase, set())
        return target in allowed

    def reset(self) -> None:
        self._state.current_phase = AgentPhase.IDLE
        self._state.status = AgentStatus.INITIALIZED
        self._state.retry_count = 0
        self._state.plan = None
        self._state.reasoning_history.clear()
        self._state.tool_call_history.clear()
        self._state.observations.clear()
        self._state.reflections.clear()
        self._state.accumulated_context.clear()
        self._state.context_token_count = 0
        self._state.intermediate_outputs.clear()
        self._state.final_output = None
        self._state.started_at = None
        self._state.current_step_started_at = None
        self._state.total_duration_ms = 0

    def get_elapsed_ms(self) -> int:
        if self._state.started_at is None:
            return 0
        delta = datetime.now(UTC) - self._state.started_at
        return int(delta.total_seconds() * 1000)


class InvalidTransitionError(Exception):
    pass
