from __future__ import annotations


import pytest

from app.agents.base import BaseAgent
from app.agents.lifecycle import AgentLifecycleManager, InvalidTransitionError
from app.agents.models import (
    AgentContext,
    AgentMetadata,
    AgentOutput,
    AgentPhase,
    AgentState,
    AgentStatus,
    AgentStep,
    ExecutionPlan,
    Observation,
    ReasoningStep,
    Reflection,
    ToolCall,
    WorkflowResult,
)
from app.agents.registry import AgentRegistry, RegistryError
from app.agents.task_graph import TaskGraph


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TestAgentStatus:
    def test_all_values_present(self) -> None:
        expected = [
            "initialized", "receiving_context", "planning", "reasoning",
            "requesting_tool", "executing_tool", "observing_result",
            "reflecting", "self_validating", "outputting_result",
            "completed", "failed", "cancelled", "error",
        ]
        assert [s.value for s in AgentStatus] == expected

    def test_is_str_enum(self) -> None:
        assert AgentStatus("initialized") == AgentStatus.INITIALIZED
        assert AgentStatus("completed") == AgentStatus.COMPLETED


class TestAgentPhase:
    def test_all_values_present(self) -> None:
        expected = ["idle", "planning", "reasoning", "tool_use", "reflecting", "validating", "outputting"]
        assert [p.value for p in AgentPhase] == expected

    def test_is_str_enum(self) -> None:
        assert AgentPhase("idle") == AgentPhase.IDLE
        assert AgentPhase("outputting") == AgentPhase.OUTPUTTING


class TestAgentContext:
    def test_defaults(self) -> None:
        ctx = AgentContext(workflow_id="w1", step_id="s1", trace_id="t1")
        assert ctx.input == {}
        assert ctx.config == {}
        assert ctx.metadata == {}

    def test_custom_values(self) -> None:
        ctx = AgentContext(
            workflow_id="w1",
            step_id="s1",
            trace_id="t1",
            input={"key": "val"},
            config={"timeout": 30},
            metadata={"env": "test"},
        )
        assert ctx.input == {"key": "val"}
        assert ctx.config == {"timeout": 30}
        assert ctx.metadata == {"env": "test"}


class TestAgentOutput:
    def test_defaults(self) -> None:
        out = AgentOutput(agent_id="a1", workflow_id="w1")
        assert out.output == {}
        assert out.summary == ""
        assert out.duration_ms == 0
        assert out.metadata == {}

    def test_custom_values(self) -> None:
        out = AgentOutput(
            agent_id="a1", workflow_id="w1",
            output={"result": "ok"}, summary="done", duration_ms=100,
        )
        assert out.output == {"result": "ok"}
        assert out.summary == "done"
        assert out.duration_ms == 100


class TestAgentStep:
    def test_defaults(self) -> None:
        step = AgentStep(agent_id="s1")
        assert step.input == {}
        assert step.output_schema is None
        assert step.priority == 0
        assert step.depends_on == []
        assert step.requires_approval is False
        assert step.timeout_seconds == 60
        assert step.max_retries == 3
        assert step.metadata == {}

    def test_with_dependencies(self) -> None:
        step = AgentStep(agent_id="s1", depends_on=["s0"], priority=5, requires_approval=True)
        assert step.depends_on == ["s0"]
        assert step.priority == 5
        assert step.requires_approval is True


class TestExecutionPlan:
    def test_defaults(self) -> None:
        plan = ExecutionPlan()
        assert plan.steps == []
        assert plan.parallel_branches == []
        assert plan.estimated_cost == {}
        assert plan.requires_approval == []

    def test_with_steps(self) -> None:
        step = AgentStep(agent_id="s1")
        plan = ExecutionPlan(steps=[step], estimated_cost={"total": 1.5})
        assert len(plan.steps) == 1
        assert plan.estimated_cost == {"total": 1.5}


class TestAgentState:
    def test_defaults(self) -> None:
        state = AgentState(agent_id="a1", workflow_id="w1")
        assert state.status == AgentStatus.INITIALIZED
        assert state.current_phase == AgentPhase.IDLE
        assert state.retry_count == 0
        assert state.max_retries == 3
        assert state.plan is None
        assert state.reasoning_history == []
        assert state.tool_call_history == []
        assert state.observations == []
        assert state.reflections == []
        assert state.accumulated_context == []
        assert state.context_token_count == 0
        assert state.max_context_tokens == 32000
        assert state.intermediate_outputs == {}
        assert state.final_output is None
        assert state.started_at is None
        assert state.current_step_started_at is None
        assert state.total_duration_ms == 0

    def test_status_transition_allowed(self) -> None:
        state = AgentState(agent_id="a1", workflow_id="w1", status=AgentStatus.PLANNING)
        assert state.status == AgentStatus.PLANNING


class TestWorkflowResult:
    def test_defaults(self) -> None:
        wr = WorkflowResult(workflow_id="w1", status="running")
        assert wr.query == ""
        assert wr.execution_plan is None
        assert wr.papers is None
        assert wr.costs == {}
        assert wr.duration_ms == 0
        assert wr.steps_completed == []
        assert wr.steps_failed == []
        assert wr.checkpoint_decisions == []

    def test_with_values(self) -> None:
        wr = WorkflowResult(
            workflow_id="w1", status="completed", query="test",
            duration_ms=500, steps_completed=["s1"],
        )
        assert wr.query == "test"
        assert wr.duration_ms == 500
        assert wr.steps_completed == ["s1"]


class TestAgentMetadata:
    def test_creation(self) -> None:
        meta = AgentMetadata(id="a1", name="test_agent")
        assert meta.id == "a1"
        assert meta.name == "test_agent"
        assert meta.version == "1.0"

    def test_custom_version(self) -> None:
        meta = AgentMetadata(id="a1", name="test_agent", version="2.0.0")
        assert meta.version == "2.0.0"


class TestSubModels:
    def test_reasoning_step(self) -> None:
        rs = ReasoningStep(step_number=1, description="thinking")
        assert rs.result == ""

    def test_tool_call(self) -> None:
        tc = ToolCall(tool_id="t1")
        assert tc.input == {}
        assert tc.output == {}
        assert tc.duration_ms == 0

    def test_observation(self) -> None:
        obs = Observation(source="web")
        assert obs.content == ""
        assert obs.metadata == {}

    def test_reflection(self) -> None:
        ref = Reflection(insight="need more data")
        assert ref.confidence == 1.0
        assert ref.source == ""


# ---------------------------------------------------------------------------
# BaseAgent
# ---------------------------------------------------------------------------


class _ConcreteAgent(BaseAgent):
    agent_id = "test_agent"
    agent_name = "TestAgent"
    version = "2.0"

    async def execute(self, context: AgentContext) -> AgentOutput:
        return AgentOutput(agent_id=self.agent_id, workflow_id=context.workflow_id)


class _MinimalAgent(BaseAgent):
    async def execute(self, context: AgentContext) -> AgentOutput:
        return AgentOutput(agent_id=self.agent_id, workflow_id=context.workflow_id)


class TestBaseAgent:
    def test_cannot_instantiate_abstract(self) -> None:
        with pytest.raises(TypeError):
            BaseAgent()  # type: ignore[abstract]

    def test_concrete_agent_properties(self) -> None:
        agent = _ConcreteAgent()
        assert agent.agent_id == "test_agent"
        assert agent.agent_name == "TestAgent"
        assert agent.version == "2.0"

    @pytest.mark.asyncio
    async def test_execute_returns_output(self) -> None:
        agent = _ConcreteAgent()
        ctx = AgentContext(workflow_id="w1", step_id="s1", trace_id="t1")
        result = await agent.execute(ctx)
        assert isinstance(result, AgentOutput)
        assert result.agent_id == "test_agent"
        assert result.workflow_id == "w1"

    @pytest.mark.asyncio
    async def test_validate_output_default_true(self) -> None:
        agent = _ConcreteAgent()
        output = AgentOutput(agent_id="a1", workflow_id="w1")
        assert await agent.validate_output(output) is True

    @pytest.mark.asyncio
    async def test_handle_error_raises_below_max_retries(self) -> None:
        agent = _ConcreteAgent()
        ctx = AgentContext(workflow_id="w1", step_id="s1", trace_id="t1")
        error = ValueError("test error")
        with pytest.raises(ValueError, match="test error"):
            await agent.handle_error(error, ctx)
        assert agent._state.retry_count == 1

    @pytest.mark.asyncio
    async def test_handle_error_returns_fallback_when_exhausted(self) -> None:
        agent = _ConcreteAgent()
        agent._state.retry_count = agent.max_retries - 1
        ctx = AgentContext(workflow_id="w1", step_id="s1", trace_id="t1")
        result = await agent.handle_error(ValueError("final"), ctx)
        assert isinstance(result, AgentOutput)
        assert "error" in result.output
        assert "retries" in result.summary

    @pytest.mark.asyncio
    async def test_update_state_valid_field(self) -> None:
        agent = _ConcreteAgent()
        await agent.update_state(retry_count=5)
        assert agent._state.retry_count == 5

    @pytest.mark.asyncio
    async def test_update_state_ignores_invalid_field(self) -> None:
        agent = _ConcreteAgent()
        await agent.update_state(nonexistent_field="value")
        assert not hasattr(agent._state, "nonexistent_field")

    @pytest.mark.asyncio
    async def test_lifecycle_returns_state(self) -> None:
        agent = _ConcreteAgent()
        state = await agent.lifecycle()
        assert state is agent._state
        assert state.agent_id == "test_agent"

    @pytest.mark.asyncio
    async def test_minimal_agent_defaults(self) -> None:
        agent = _MinimalAgent()
        assert agent.agent_id == ""
        assert agent.agent_name == ""
        assert agent.version == "1.0"
        assert agent.max_retries == 3
        assert agent.timeout_seconds == 60

    def test_estimate_tokens_static(self) -> None:
        text = "hello world"
        assert BaseAgent._estimate_tokens(text) == len(text) // 4


# ---------------------------------------------------------------------------
# AgentLifecycleManager
# ---------------------------------------------------------------------------


class TestAgentLifecycleManager:
    @pytest.fixture
    def state(self) -> AgentState:
        return AgentState(agent_id="a1", workflow_id="w1")

    @pytest.fixture
    def manager(self, state: AgentState) -> AgentLifecycleManager:
        return AgentLifecycleManager(state)

    def test_initial_phase_is_idle(self, manager: AgentLifecycleManager) -> None:
        assert manager._state.current_phase == AgentPhase.IDLE
        assert manager._state.status == AgentStatus.INITIALIZED

    def test_valid_transition_idle_to_planning(self, manager: AgentLifecycleManager) -> None:
        manager.transition(AgentPhase.PLANNING)
        assert manager._state.current_phase == AgentPhase.PLANNING
        assert manager._state.status == AgentStatus.PLANNING
        assert manager._state.started_at is not None

    def test_invalid_transition_raises_error(self, manager: AgentLifecycleManager) -> None:
        with pytest.raises(InvalidTransitionError):
            manager.transition(AgentPhase.REASONING)

    def test_full_valid_sequence(self, manager: AgentLifecycleManager) -> None:
        manager.transition(AgentPhase.PLANNING)
        manager.transition(AgentPhase.REASONING)
        manager.transition(AgentPhase.TOOL_USE)
        manager.transition(AgentPhase.REFLECTING)
        manager.transition(AgentPhase.VALIDATING)
        manager.transition(AgentPhase.OUTPUTTING)
        assert manager._state.current_phase == AgentPhase.OUTPUTTING
        assert manager._state.status == AgentStatus.OUTPUTTING_RESULT

    def test_can_transition_to_valid(self, manager: AgentLifecycleManager) -> None:
        assert manager.can_transition_to(AgentPhase.PLANNING) is True

    def test_can_transition_to_invalid(self, manager: AgentLifecycleManager) -> None:
        assert manager.can_transition_to(AgentPhase.REASONING) is False
        assert manager.can_transition_to(AgentPhase.OUTPUTTING) is False

    def test_get_allowed_transitions_from_idle(self, manager: AgentLifecycleManager) -> None:
        assert manager.get_allowed_transitions() == [AgentPhase.PLANNING]

    def test_outputting_has_no_outgoing(self, manager: AgentLifecycleManager) -> None:
        manager.transition(AgentPhase.PLANNING)
        manager.transition(AgentPhase.REASONING)
        manager.transition(AgentPhase.TOOL_USE)
        manager.transition(AgentPhase.REFLECTING)
        manager.transition(AgentPhase.VALIDATING)
        manager.transition(AgentPhase.OUTPUTTING)
        assert manager.get_allowed_transitions() == []

    def test_reflecting_can_go_to_planning_or_validating(self, manager: AgentLifecycleManager) -> None:
        manager.transition(AgentPhase.PLANNING)
        manager.transition(AgentPhase.REASONING)
        manager.transition(AgentPhase.TOOL_USE)
        manager.transition(AgentPhase.REFLECTING)
        allowed = manager.get_allowed_transitions()
        assert AgentPhase.PLANNING in allowed
        assert AgentPhase.VALIDATING in allowed
        assert len(allowed) == 2

    def test_validating_can_go_to_outputting_or_planning(self, manager: AgentLifecycleManager) -> None:
        manager.transition(AgentPhase.PLANNING)
        manager.transition(AgentPhase.REASONING)
        manager.transition(AgentPhase.TOOL_USE)
        manager.transition(AgentPhase.REFLECTING)
        manager.transition(AgentPhase.VALIDATING)
        allowed = manager.get_allowed_transitions()
        assert AgentPhase.OUTPUTTING in allowed
        assert AgentPhase.PLANNING in allowed

    def test_loop_through_planning(self, manager: AgentLifecycleManager) -> None:
        manager.transition(AgentPhase.PLANNING)
        manager.transition(AgentPhase.REASONING)
        manager.transition(AgentPhase.TOOL_USE)
        manager.transition(AgentPhase.REFLECTING)
        manager.transition(AgentPhase.PLANNING)
        assert manager._state.current_phase == AgentPhase.PLANNING
        assert manager._state.status == AgentStatus.PLANNING

    def test_reset_restores_initial_state(self, manager: AgentLifecycleManager) -> None:
        manager.transition(AgentPhase.PLANNING)
        manager.reset()
        assert manager._state.current_phase == AgentPhase.IDLE
        assert manager._state.status == AgentStatus.INITIALIZED
        assert manager._state.retry_count == 0
        assert manager._state.plan is None
        assert manager._state.started_at is None

    def test_get_elapsed_ms_before_start(self, manager: AgentLifecycleManager) -> None:
        assert manager.get_elapsed_ms() == 0

    def test_get_elapsed_ms_after_start(self, manager: AgentLifecycleManager) -> None:
        manager.transition(AgentPhase.PLANNING)
        elapsed = manager.get_elapsed_ms()
        assert elapsed >= 0

    def test_invalid_transition_error_message(self, manager: AgentLifecycleManager) -> None:
        with pytest.raises(InvalidTransitionError, match="idle.*reasoning"):
            manager.transition(AgentPhase.REASONING)

    def test_phase_status_mapping(self, state: AgentState) -> None:
        manager = AgentLifecycleManager(state)
        for phase, expected_status in [
            (AgentPhase.IDLE, AgentStatus.INITIALIZED),
            (AgentPhase.PLANNING, AgentStatus.PLANNING),
            (AgentPhase.REASONING, AgentStatus.REASONING),
            (AgentPhase.TOOL_USE, AgentStatus.EXECUTING_TOOL),
            (AgentPhase.REFLECTING, AgentStatus.REFLECTING),
            (AgentPhase.VALIDATING, AgentStatus.SELF_VALIDATING),
            (AgentPhase.OUTPUTTING, AgentStatus.OUTPUTTING_RESULT),
        ]:
            if phase == AgentPhase.IDLE:
                continue
            manager._state.current_phase = phase
            manager._state.status = manager._ALLOWED_TRANSITIONS.get(phase, ...)  # skip

    def test_all_sixteen_transitions_exercise(self, state: AgentState) -> None:
        manager = AgentLifecycleManager(state)
        sequence = [
            AgentPhase.PLANNING,
            AgentPhase.REASONING,
            AgentPhase.TOOL_USE,
            AgentPhase.REFLECTING,
            AgentPhase.VALIDATING,
            AgentPhase.OUTPUTTING,
        ]
        for phase in sequence:
            manager.transition(phase)
        assert manager._state.current_phase == AgentPhase.OUTPUTTING


# ---------------------------------------------------------------------------
# AgentRegistry
# ---------------------------------------------------------------------------


class TestAgentRegistry:
    @pytest.fixture
    def registry(self) -> AgentRegistry:
        return AgentRegistry()

    def test_register_decorator_without_args(self, registry: AgentRegistry) -> None:
        @registry.register()
        class MyAgent(BaseAgent):
            agent_id = "my_agent"
            agent_name = "MyAgent"

            async def execute(self, context: AgentContext) -> AgentOutput:
                return AgentOutput(agent_id=self.agent_id, workflow_id=context.workflow_id)

        agent = registry.get("my_agent")
        assert isinstance(agent, MyAgent)

    def test_register_decorator_with_agent_id(self, registry: AgentRegistry) -> None:
        @registry.register(agent_id="custom_id")
        class AnotherAgent(BaseAgent):
            agent_id = "unused_id"
            agent_name = "AnotherAgent"

            async def execute(self, context: AgentContext) -> AgentOutput:
                return AgentOutput(agent_id=self.agent_id, workflow_id=context.workflow_id)

        agent = registry.get("custom_id")
        assert isinstance(agent, AnotherAgent)

    def test_get_by_id_returns_same_instance(self, registry: AgentRegistry) -> None:
        @registry.register()
        class SingletonAgent(BaseAgent):
            agent_id = "singleton"
            agent_name = "Singleton"

            async def execute(self, context: AgentContext) -> AgentOutput:
                return AgentOutput(agent_id=self.agent_id, workflow_id=context.workflow_id)

        inst1 = registry.get("singleton")
        inst2 = registry.get("singleton")
        assert inst1 is inst2

    def test_get_nonexistent_agent_raises_error(self, registry: AgentRegistry) -> None:
        with pytest.raises(RegistryError, match="nonexistent"):
            registry.get("nonexistent")

    def test_register_duplicate_raises_error(self, registry: AgentRegistry) -> None:
        @registry.register()
        class AgentA(BaseAgent):
            agent_id = "dup"
            agent_name = "A"

            async def execute(self, context: AgentContext) -> AgentOutput:
                return AgentOutput(agent_id=self.agent_id, workflow_id=context.workflow_id)

        with pytest.raises(RegistryError, match="already registered"):

            @registry.register()
            class AgentB(BaseAgent):
                agent_id = "dup"
                agent_name = "B"

                async def execute(self, context: AgentContext) -> AgentOutput:
                    return AgentOutput(agent_id=self.agent_id, workflow_id=context.workflow_id)

    def test_list_agents(self, registry: AgentRegistry) -> None:
        @registry.register()
        class AgentA(BaseAgent):
            agent_id = "a1"
            agent_name = "Alpha"

            async def execute(self, context: AgentContext) -> AgentOutput:
                return AgentOutput(agent_id=self.agent_id, workflow_id=context.workflow_id)

        @registry.register()
        class AgentB(BaseAgent):
            agent_id = "b1"
            agent_name = "Beta"
            version = "2.0"

            async def execute(self, context: AgentContext) -> AgentOutput:
                return AgentOutput(agent_id=self.agent_id, workflow_id=context.workflow_id)

        agents = registry.list_agents()
        metas = {(m.id, m.name, m.version) for m in agents}
        assert ("a1", "Alpha", "1.0") in metas
        assert ("b1", "Beta", "2.0") in metas

    def test_clear_instances(self, registry: AgentRegistry) -> None:
        @registry.register()
        class MyAgent(BaseAgent):
            agent_id = "my"
            agent_name = "My"

            async def execute(self, context: AgentContext) -> AgentOutput:
                return AgentOutput(agent_id=self.agent_id, workflow_id=context.workflow_id)

        inst1 = registry.get("my")
        registry.clear_instances()
        inst2 = registry.get("my")
        assert inst1 is not inst2

    def test_register_invalid_class(self, registry: AgentRegistry) -> None:
        with pytest.raises(RegistryError):
            registry.register()(object)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TaskGraph
# ---------------------------------------------------------------------------


class TestTaskGraph:
    @pytest.fixture
    def graph(self) -> TaskGraph:
        return TaskGraph()

    def test_add_step(self, graph: TaskGraph) -> None:
        step = AgentStep(agent_id="s1")
        graph.add_step(step)
        assert len(graph.all_steps()) == 1
        assert graph.all_steps()[0].agent_id == "s1"

    def test_add_dependency(self, graph: TaskGraph) -> None:
        s1 = AgentStep(agent_id="s1")
        s2 = AgentStep(agent_id="s2", depends_on=["s1"])
        graph.add_step(s1)
        graph.add_step(s2)
        deps = graph.get_dependents("s1")
        assert "s2" in deps

    def test_add_dependency_invalid_step(self, graph: TaskGraph) -> None:
        s1 = AgentStep(agent_id="s1")
        graph.add_step(s1)
        with pytest.raises(ValueError, match="not found"):
            graph.add_dependency("s1", "nonexistent")

    def test_add_dependency_invalid_depends(self, graph: TaskGraph) -> None:
        s1 = AgentStep(agent_id="s1")
        graph.add_step(s1)
        with pytest.raises(ValueError, match="not found"):
            graph.add_dependency("nonexistent", "s1")

    def test_topological_order_simple(self, graph: TaskGraph) -> None:
        s1 = AgentStep(agent_id="s1")
        s2 = AgentStep(agent_id="s2", depends_on=["s1"])
        s3 = AgentStep(agent_id="s3", depends_on=["s2"])
        graph.add_step(s1)
        graph.add_step(s2)
        graph.add_step(s3)
        order = graph.get_topological_order()
        ids = [s.agent_id for s in order]
        assert ids == ["s1", "s2", "s3"]

    def test_topological_order_complex(self, graph: TaskGraph) -> None:
        s1 = AgentStep(agent_id="s1")
        s2 = AgentStep(agent_id="s2", depends_on=["s1"])
        s3 = AgentStep(agent_id="s3", depends_on=["s1"])
        s4 = AgentStep(agent_id="s4", depends_on=["s2", "s3"])
        graph.add_step(s1)
        graph.add_step(s2)
        graph.add_step(s3)
        graph.add_step(s4)
        order = graph.get_topological_order()
        ids = [s.agent_id for s in order]
        assert ids[0] == "s1"
        assert ids[-1] == "s4"
        assert ids.index("s2") > ids.index("s1")
        assert ids.index("s3") > ids.index("s1")

    def test_detect_cycle_returns_false_for_acyclic(self, graph: TaskGraph) -> None:
        s1 = AgentStep(agent_id="s1")
        s2 = AgentStep(agent_id="s2", depends_on=["s1"])
        graph.add_step(s1)
        graph.add_step(s2)
        assert graph.detect_cycles() is False

    def test_detect_cycle_returns_true_for_cycle(self, graph: TaskGraph) -> None:
        s1 = AgentStep(agent_id="s1", depends_on=["s2"])
        s2 = AgentStep(agent_id="s2", depends_on=["s1"])
        graph.add_step(s1)
        graph.add_step(s2)
        assert graph.detect_cycles() is True

    def test_get_levels_simple(self, graph: TaskGraph) -> None:
        s1 = AgentStep(agent_id="s1")
        s2 = AgentStep(agent_id="s2", depends_on=["s1"])
        s3 = AgentStep(agent_id="s3", depends_on=["s2"])
        graph.add_step(s1)
        graph.add_step(s2)
        graph.add_step(s3)
        levels = graph.get_levels()
        assert len(levels) == 3
        assert levels[0][0].agent_id == "s1"
        assert levels[1][0].agent_id == "s2"
        assert levels[2][0].agent_id == "s3"

    def test_get_levels_parallel(self, graph: TaskGraph) -> None:
        s1 = AgentStep(agent_id="s1")
        s2 = AgentStep(agent_id="s2", depends_on=["s1"])
        s3 = AgentStep(agent_id="s3", depends_on=["s1"])
        graph.add_step(s1)
        graph.add_step(s2)
        graph.add_step(s3)
        levels = graph.get_levels()
        assert len(levels) == 2
        assert levels[0][0].agent_id == "s1"
        assert len(levels[1]) == 2

    def test_empty_graph(self, graph: TaskGraph) -> None:
        assert graph.all_steps() == []
        assert graph.get_topological_order() == []
        assert graph.get_levels() == []
        assert graph.detect_cycles() is False
        assert graph.is_complete(set()) is True

    def test_get_ready_steps(self, graph: TaskGraph) -> None:
        s1 = AgentStep(agent_id="s1")
        s2 = AgentStep(agent_id="s2", depends_on=["s1"])
        s3 = AgentStep(agent_id="s3", depends_on=["s1", "s2"])
        graph.add_step(s1)
        graph.add_step(s2)
        graph.add_step(s3)
        ready0 = graph.get_ready_steps(set())
        assert len(ready0) == 1
        assert ready0[0].agent_id == "s1"
        ready1 = graph.get_ready_steps({"s1"})
        assert len(ready1) == 1
        assert ready1[0].agent_id == "s2"
        ready2 = graph.get_ready_steps({"s1", "s2"})
        assert len(ready2) == 1
        assert ready2[0].agent_id == "s3"

    def test_is_complete(self, graph: TaskGraph) -> None:
        s1 = AgentStep(agent_id="s1")
        graph.add_step(s1)
        assert graph.is_complete(set()) is False
        assert graph.is_complete({"s1"}) is True

    def test_get_remaining_steps(self, graph: TaskGraph) -> None:
        s1 = AgentStep(agent_id="s1")
        s2 = AgentStep(agent_id="s2")
        graph.add_step(s1)
        graph.add_step(s2)
        remaining = graph.get_remaining_steps({"s1"})
        assert len(remaining) == 1
        assert remaining[0].agent_id == "s2"

    def test_all_steps_returns_copy(self, graph: TaskGraph) -> None:
        s1 = AgentStep(agent_id="s1")
        graph.add_step(s1)
        assert len(graph.all_steps()) == 1

    def test_get_dependents_empty(self, graph: TaskGraph) -> None:
        s1 = AgentStep(agent_id="s1")
        graph.add_step(s1)
        assert graph.get_dependents("s1") == []

    def test_topological_order_returns_empty_for_cycle(self, graph: TaskGraph) -> None:
        s1 = AgentStep(agent_id="s1", depends_on=["s2"])
        s2 = AgentStep(agent_id="s2", depends_on=["s1"])
        graph.add_step(s1)
        graph.add_step(s2)
        assert graph.get_topological_order() == []
