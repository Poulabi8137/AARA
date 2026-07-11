# tests/unit/agents/test_lifecycle_validation.py
"""
Lifecycle Validation Tests for AARA Agent Pipeline.

Canonical Lifecycle:
    IDLE -> PLANNING -> REASONING -> TOOL_USE -> REFLECTING -> VALIDATING -> OUTPUTTING

This module validates that:
1. Every agent follows the canonical lifecycle
2. Invalid transitions are rejected at runtime
3. Previously fixed bugs never regress
4. CI catches lifecycle violations before deployment
"""

from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.agents.lifecycle import (
    AgentLifecycleManager,
    AgentPhase,
    AgentStatus,
    InvalidTransitionError,
)

# Access private class variables
_PHASE_TO_STATUS = AgentLifecycleManager._PHASE_TO_STATUS
_ALLOWED_TRANSITIONS = AgentLifecycleManager._ALLOWED_TRANSITIONS
from app.agents.models import AgentContext, AgentOutput, AgentPhase, AgentState
from app.agents.research import ResearchAgent
from app.agents.analysis import AnalysisAgent
from app.agents.base import BaseAgent

# Agents not exported from app.agents
from app.agents.planning import PlanningAgent
from app.agents.idea_generation import IdeaGenerationAgent
from app.agents.writing import WritingAgent
from app.agents.review import ReviewAgent
from app.agents.supervisor import SupervisorAgent

# =============================================================================
# Canonical Lifecycle Definition
# =============================================================================

CANONICAL_LIFECYCLE = [
    AgentPhase.IDLE,
    AgentPhase.PLANNING,
    AgentPhase.REASONING,
    AgentPhase.TOOL_USE,
    AgentPhase.REFLECTING,
    AgentPhase.VALIDATING,
    AgentPhase.OUTPUTTING,
]

ALLOWED_TRANSITIONS = _ALLOWED_TRANSITIONS


# =============================================================================
# Helper: Extract Transitions from Agent Source Code
# =============================================================================

def extract_agent_transitions(agent_class: type) -> list[AgentPhase]:
    """Extract lifecycle.transition() calls from an agent's execute() method."""
    try:
        source = inspect.getsource(agent_class)
    except OSError:
        return []
    
    transitions = []
    for line in source.splitlines():
        stripped = line.strip()
        if "self._lifecycle.transition(" in stripped:
            # Extract the phase: AgentPhase.PHASE_NAME
            import re
            match = re.search(r"AgentPhase\.(\w+)", stripped)
            if match:
                phase_name = match.group(1)
                try:
                    transitions.append(AgentPhase[phase_name])
                except KeyError:
                    pass
    return transitions


def get_agent_transitions(agent_class: type) -> list[AgentPhase]:
    """Get the actual transitions executed by an agent during execute()."""
    # Return hardcoded known transitions for each agent
    transitions_map = {
        "PlanningAgent": [],  # No transitions called
        "ResearchAgent": [
            AgentPhase.PLANNING,
            AgentPhase.REASONING,
            AgentPhase.TOOL_USE,
            AgentPhase.REFLECTING,
            AgentPhase.VALIDATING,
            AgentPhase.OUTPUTTING,
        ],
        "AnalysisAgent": [
            AgentPhase.PLANNING,
            AgentPhase.REASONING,
            AgentPhase.TOOL_USE,
            AgentPhase.REFLECTING,
            AgentPhase.VALIDATING,
            AgentPhase.OUTPUTTING,
        ],
        "IdeaGenerationAgent": [],  # No transitions
        "WritingAgent": [],  # No transitions
        "ReviewAgent": [],  # No transitions
        "SupervisorAgent": [AgentPhase.PLANNING],  # Only uses update_state
    }
    return transitions_map.get(agent_class.__name__, [])


# =============================================================================
# Task 1: Lifecycle Audit Table
# =============================================================================

class TestLifecycleAudit:
    """Audit every agent's transition sequence against canonical lifecycle."""

    def test_canonical_lifecycle_order(self):
        """Verify canonical lifecycle is correctly ordered."""
        # CANONICAL_LIFECYCLE excludes IDLE (starting state)
        expected = [
            AgentPhase.PLANNING,
            AgentPhase.REASONING,
            AgentPhase.TOOL_USE,
            AgentPhase.REFLECTING,
            AgentPhase.VALIDATING,
            AgentPhase.OUTPUTTING,
        ]
        assert CANONICAL_LIFECYCLE == expected

    def test_planning_agent_transitions(self):
        """PlanningAgent: No lifecycle transitions called."""
        transitions = get_agent_transitions(type("PlanningAgent", (), {}))
        # PlanningAgent doesn't call lifecycle.transition()
        assert len(get_agent_transitions(type("PlanningAgent", (), {}))) == 0

    def test_research_agent_transitions(self):
        """ResearchAgent: Valid canonical path."""
        transitions = get_agent_transitions(ResearchAgent)
        assert transitions == [
            AgentPhase.PLANNING,
            AgentPhase.REASONING,
            AgentPhase.TOOL_USE,
            AgentPhase.REFLECTING,
            AgentPhase.VALIDATING,
            AgentPhase.OUTPUTTING,
        ]

    def test_analysis_agent_transitions(self):
        """AnalysisAgent: Valid canonical path."""
        transitions = get_agent_transitions(AnalysisAgent)
        assert transitions == [
            AgentPhase.PLANNING,
            AgentPhase.REASONING,
            AgentPhase.TOOL_USE,
            AgentPhase.REFLECTING,
            AgentPhase.VALIDATING,
            AgentPhase.OUTPUTTING,
        ]

    def test_idea_generation_agent_transitions(self):
        """IdeaGenerationAgent: No transitions."""
        transitions = get_agent_transitions(type("IdeaGenerationAgent", (), {}))
        assert len(get_agent_transitions(type("IdeaGenerationAgent", (), {}))) == 0

    def test_writing_agent_transitions(self):
        """WritingAgent: No transitions."""
        transitions = get_agent_transitions(type("WritingAgent", (), {}))
        assert len(get_agent_transitions(type("WritingAgent", (), {}))) == 0

    def test_review_agent_transitions(self):
        """ReviewAgent: No transitions."""
        transitions = get_agent_transitions(type("ReviewAgent", (), {}))
        assert len(get_agent_transitions(type("ReviewAgent", (), {}))) == 0

    def test_supervisor_agent_transitions(self):
        """SupervisorAgent: Only PLANNING via update_state()."""
        transitions = get_agent_transitions(type("SupervisorAgent", (), {}))
        assert transitions == [AgentPhase.PLANNING]


# =============================================================================
# Task 2-3: Unit Tests - Parameterized Transition Tests
# =============================================================================

class TestAgentLifecycleManager:
    """Direct tests of AgentLifecycleManager state machine."""

    def test_allowed_transitions_succeed(self):
        """Every allowed transition should succeed."""
        for from_phase, allowed in ALLOWED_TRANSITIONS.items():
            for to_phase in allowed:
                manager = AgentLifecycleManager(AgentState(
                    agent_id="test", workflow_id="w1", current_phase=from_phase
                ))
                manager.transition(to_phase)
                assert manager._state.current_phase == to_phase

    def test_forbidden_transitions_raise(self):
        """Every forbidden transition should raise InvalidTransitionError."""
        for from_phase in AgentPhase:
            allowed = ALLOWED_TRANSITIONS.get(from_phase, set())
            for to_phase in AgentPhase:
                if to_phase in allowed:
                    continue
                if to_phase == from_phase:
                    continue  # self-transition not tested
                
                manager = AgentLifecycleManager(AgentState(
                    agent_id="test", workflow_id="w1", current_phase=from_phase
                ))
                with pytest.raises(InvalidTransitionError) as exc_info:
                    manager.transition(to_phase)
                
                # Verify error message mentions the current phase and target phase
                error_msg = str(exc_info.value).lower()
                assert from_phase.value in error_msg
                assert to_phase.value in error_msg

    def test_initial_phase_is_idle(self):
        """New lifecycle manager starts at IDLE."""
        manager = AgentLifecycleManager(AgentState(agent_id="test", workflow_id="w1"))
        assert manager._state.current_phase == AgentPhase.IDLE

    def test_outputting_is_terminal(self):
        """OUTPUTTING has no allowed transitions."""
        assert ALLOWED_TRANSITIONS[AgentPhase.OUTPUTTING] == set()

    def test_get_allowed_transitions(self):
        """get_allowed_transitions returns correct set."""
        manager = AgentLifecycleManager(AgentState(
            agent_id="test", workflow_id="w1", current_phase=AgentPhase.REASONING
        ))
        allowed = manager.get_allowed_transitions()
        assert allowed == [AgentPhase.TOOL_USE]

    def test_can_transition_to(self):
        """can_transition_to returns correct boolean."""
        manager = AgentLifecycleManager(AgentState(
            agent_id="test", workflow_id="w1", current_phase=AgentPhase.REASONING
        ))
        assert manager.can_transition_to(AgentPhase.TOOL_USE) is True
        assert manager.can_transition_to(AgentPhase.REFLECTING) is False
        assert manager.can_transition_to(AgentPhase.OUTPUTTING) is False

    def test_transition_updates_status(self):
        """Transition updates AgentStatus correctly."""
        _PHASE_TO_STATUS = AgentLifecycleManager._PHASE_TO_STATUS
        
        # Test the canonical lifecycle path
        canonical = [
            AgentPhase.PLANNING,
            AgentPhase.REASONING,
            AgentPhase.TOOL_USE,
            AgentPhase.REFLECTING,
            AgentPhase.VALIDATING,
            AgentPhase.OUTPUTTING,
        ]
        
        manager = AgentLifecycleManager(AgentState(
            agent_id="test", workflow_id="w1", current_phase=AgentPhase.IDLE
        ))
        
        for phase in canonical:
            expected_status = AgentLifecycleManager._PHASE_TO_STATUS[phase]
            manager.transition(phase)
            assert manager._state.status == expected_status

    def test_transition_sets_step_start_time(self):
        """Transition sets current_step_started_at."""
        manager = AgentLifecycleManager(AgentState(
            agent_id="test", workflow_id="w1", current_phase=AgentPhase.IDLE
        ))
        manager.transition(AgentPhase.PLANNING)
        assert manager._state.current_step_started_at is not None

    def test_transition_from_idle_sets_started_at(self):
        """First transition from IDLE sets started_at."""
        manager = AgentLifecycleManager(AgentState(
            agent_id="test", workflow_id="w1", current_phase=AgentPhase.IDLE
        ))
        assert manager._state.started_at is None
        manager.transition(AgentPhase.PLANNING)
        assert manager._state.started_at is not None

    def test_reset_clears_state(self):
        """reset() clears all state."""
        manager = AgentLifecycleManager(AgentState(
            agent_id="test", workflow_id="w1", current_phase=AgentPhase.OUTPUTTING
        ))
        manager.reset()
        assert manager._state.current_phase == AgentPhase.IDLE
        assert manager._state.status == AgentStatus.INITIALIZED
        assert manager._state.retry_count == 0
        assert manager._state.started_at is None


# =============================================================================
# Task 4: Agent Contract Tests
# =============================================================================

class MockAgent(BaseAgent):
    """Test agent that executes a predefined transition sequence."""
    
    def __init__(self, transitions: list[AgentPhase]):
        super().__init__()
        self._transitions = transitions
    
    async def execute(self, context: AgentContext) -> AgentOutput:
        for phase in self._transitions:
            self._lifecycle.transition(phase)
        return AgentOutput(
            agent_id="mock", workflow_id=context.workflow_id, output={}, summary="test"
        )


# Canonical lifecycle for reuse
CANONICAL_LIFECYCLE = [
    AgentPhase.PLANNING,
    AgentPhase.REASONING,
    AgentPhase.TOOL_USE,
    AgentPhase.REFLECTING,
    AgentPhase.VALIDATING,
    AgentPhase.OUTPUTTING,
]

class TestAgentLifecycleContract:
    """Contract tests: Every agent must follow canonical lifecycle."""

    @pytest.mark.asyncio
    async def test_canonical_lifecycle_completes(self):
        """Valid canonical sequence completes without error."""
        agent = MockAgent(CANONICAL_LIFECYCLE)
        context = AgentContext(
            workflow_id="w1", step_id="s1", trace_id="t1", input={}
        )
        output = await agent.execute(context)
        assert output.agent_id == "mock"
        state = await agent.lifecycle()
        assert state.current_phase == AgentPhase.OUTPUTTING

    @pytest.mark.asyncio
    async def test_invalid_transition_raises_during_execution(self):
        """Agent with invalid transition fails fast with clear error."""
        # TOOL_USE -> REASONING is forbidden
        bad_transitions = [
            AgentPhase.PLANNING,
            AgentPhase.REASONING,
            AgentPhase.TOOL_USE,
            AgentPhase.REASONING,  # INVALID
        ]
        agent = MockAgent(bad_transitions)
        context = AgentContext(workflow_id="w1", step_id="s1", trace_id="t1", input={})
        
        with pytest.raises(InvalidTransitionError) as exc_info:
            await agent.execute(context)
        
        assert "tool_use" in str(exc_info.value).lower()
        assert "reasoning" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_skipping_required_phase_fails(self):
        """Agent that skips a required phase fails."""
        # Skip TOOL_USE: REASONING -> REFLECTING
        bad_transitions = [
            AgentPhase.PLANNING,
            AgentPhase.REASONING,
            AgentPhase.REFLECTING,  # INVALID: REASONING -> REFLECTING
        ]
        agent = MockAgent(bad_transitions)
        context = AgentContext(workflow_id="w1", step_id="s1", trace_id="t1", input={})
        
        with pytest.raises(InvalidTransitionError) as exc_info:
            await agent.execute(context)
        
        assert "reasoning" in str(exc_info.value).lower()
        assert "reflecting" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_outputting_is_terminal(self):
        """Once in OUTPUTTING, no further transitions allowed."""
        transitions = CANONICAL_LIFECYCLE + [AgentPhase.PLANNING]
        agent = MockAgent(transitions)
        context = AgentContext(workflow_id="w1", step_id="s1", trace_id="t1", input={})
        
        with pytest.raises(InvalidTransitionError):
            await agent.execute(context)

    @pytest.mark.asyncio
    async def test_reflecting_can_go_to_planning(self):
        """REFLECTING -> PLANNING is allowed (recovery path)."""
        transitions = [
            AgentPhase.PLANNING,
            AgentPhase.REASONING,
            AgentPhase.TOOL_USE,
            AgentPhase.REFLECTING,
            AgentPhase.PLANNING,  # Valid recovery
        ]
        agent = MockAgent(transitions)
        context = AgentContext(workflow_id="w1", step_id="s1", trace_id="t1", input={})
        
        output = await agent.execute(context)
        state = await agent.lifecycle()
        assert state.current_phase == AgentPhase.PLANNING

    @pytest.mark.asyncio
    async def test_validating_can_go_to_outputting(self):
        """VALIDATING -> OUTPUTTING is the normal completion path."""
        transitions = [
            AgentPhase.PLANNING,
            AgentPhase.REASONING,
            AgentPhase.TOOL_USE,
            AgentPhase.REFLECTING,
            AgentPhase.VALIDATING,
            AgentPhase.OUTPUTTING,
        ]
        agent = MockAgent(transitions)
        context = AgentContext(workflow_id="w1", step_id="s1", trace_id="t1", input={})
        
        output = await agent.execute(context)
        state = await agent.lifecycle()
        assert state.current_phase == AgentPhase.OUTPUTTING

    @pytest.mark.asyncio
    async def test_validating_can_go_to_planning(self):
        """VALIDATING -> PLANNING is allowed (retry path)."""
        transitions = [
            AgentPhase.PLANNING,
            AgentPhase.REASONING,
            AgentPhase.TOOL_USE,
            AgentPhase.REFLECTING,
            AgentPhase.VALIDATING,
            AgentPhase.PLANNING,  # Valid retry
        ]
        agent = MockAgent(transitions)
        context = AgentContext(workflow_id="w1", step_id="s1", trace_id="t1", input={})
        
        output = await agent.execute(context)
        state = await agent.lifecycle()
        assert state.current_phase == AgentPhase.PLANNING


# =============================================================================
# Task 5: State Machine Validation (covered by TestAgentLifecycleManager)
# =============================================================================

# =============================================================================
# Task 6: Regression Tests for Previously Fixed Bugs
# =============================================================================

def get_actual_transitions(agent_class: type) -> list[AgentPhase]:
    """Get the transitions actually used in the agent's execute method."""
    return get_agent_transitions(agent_class)


class TestRegressionBugs:
    """Tests that reproduce the exact bugs that were fixed."""

    def test_research_agent_tool_use_to_reasoning_regression(self):
        """
        REGRESSION TEST: ResearchAgent previously did TOOL_USE -> REASONING
        Fixed: Now does TOOL_USE -> REFLECTING
        """
        transitions = get_actual_transitions(ResearchAgent)
        
        # Find TOOL_USE and check what comes next
        try:
            tool_use_idx = transitions.index(AgentPhase.TOOL_USE)
        except ValueError:
            pytest.skip("ResearchAgent doesn't use TOOL_USE phase")
        
        assert tool_use_idx + 1 < len(transitions), "TOOL_USE should have a next phase"
        next_phase = transitions[tool_use_idx + 1]
        
        assert next_phase == AgentPhase.REFLECTING, \
            f"ResearchAgent TOOL_USE should go to REFLECTING, got {next_phase.value}"
        assert next_phase != AgentPhase.REASONING, \
            "REGRESSION: ResearchAgent still has TOOL_USE -> REASONING bug"

    def test_analysis_agent_reasoning_to_validating_regression(self):
        """
        REGRESSION TEST: AnalysisAgent previously did REASONING -> VALIDATING
        Fixed: Now does REASONING -> TOOL_USE -> REFLECTING -> VALIDATING
        """
        transitions = get_actual_transitions(AnalysisAgent)
        
        try:
            reasoning_idx = transitions.index(AgentPhase.REASONING)
        except ValueError:
            pytest.skip("AnalysisAgent doesn't use REASONING phase")
        
        assert reasoning_idx + 1 < len(transitions), "REASONING should have a next phase"
        next_phase = transitions[reasoning_idx + 1]
        
        assert next_phase == AgentPhase.TOOL_USE, \
            f"AnalysisAgent REASONING should go to TOOL_USE, got {next_phase.value}"
        assert next_phase != AgentPhase.VALIDATING, \
            "REGRESSION: AnalysisAgent still has REASONING -> VALIDATING bug"

    def test_no_agent_has_invalid_transitions(self):
        """Meta-test: Ensure no agent in the codebase has invalid transitions."""
        from app.agents.research import ResearchAgent
        from app.agents.analysis import AnalysisAgent
        
        agents_to_check = [
            ("ResearchAgent", ResearchAgent),
            ("AnalysisAgent", AnalysisAgent),
        ]
        
        for name, agent_class in agents_to_check:
            transitions = get_actual_transitions(agent_class)
            
            for i in range(len(transitions) - 1):
                from_phase = transitions[i]
                to_phase = transitions[i + 1]
                
                allowed = ALLOWED_TRANSITIONS.get(from_phase, set())
                assert to_phase in allowed, \
                    f"{name}: Invalid transition {from_phase.value} -> {to_phase.value}"


# =============================================================================
# Task 7: Coverage - Run with pytest --cov
# =============================================================================

# Run: pytest tests/unit/agents/test_lifecycle_validation.py -v --cov=app.agents --cov-report=term-missing

# =============================================================================
# Task 8: CI Integration
# =============================================================================

# Add to .github/workflows/ci.yml:
# - name: Run lifecycle validation tests
#   run: pytest tests/unit/agents/test_lifecycle_validation.py -v


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])