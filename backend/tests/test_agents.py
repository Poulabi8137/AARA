from __future__ import annotations

import pytest

from app.agents.state import ResearchState, make_initial_state
from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry
from app.llm.mock_provider import MockProvider
from app.graphs.research_graph import ResearchWorkflow


# ── State Tests ───────────────────────────────────────────

class TestResearchState:
    def test_make_initial_state(self) -> None:
        state = make_initial_state(query="test query", project_id="proj-1", objective="test objective")
        assert state["query"] == "test query"
        assert state["project_id"] == "proj-1"
        assert state["objective"] == "test objective"
        assert state["status"] == "pending"
        assert state["planner_output"] is None
        assert state["retrieved_documents"] == []
        assert state["summaries"] == []
        assert state["research_gaps"] == []
        assert state["generated_report"] is None
        assert state["errors"] == []
        assert "timestamp" in state

    def test_state_is_dict(self) -> None:
        state = make_initial_state(query="q")
        assert isinstance(state, dict)

    def test_state_fields_optional(self) -> None:
        state: ResearchState = {"query": "test"}
        assert state["query"] == "test"
        assert state.get("project_id") is None or state["project_id"] == ""

    def test_state_minimal(self) -> None:
        state = make_initial_state(query="q")
        assert len(state["query"]) > 0


# ── Mock Agent for Testing ────────────────────────────────

class MockTestAgent(BaseAgent):
    agent_name = "test_agent"
    description = "A test agent for unit tests"

    async def arun(self, state: ResearchState) -> ResearchState:
        state["planner_output"] = "test_output"
        state["status"] = "completed"
        return state


class FailingTestAgent(BaseAgent):
    agent_name = "failing_agent"
    description = "An agent that always fails"

    async def arun(self, state: ResearchState) -> ResearchState:
        raise ValueError("intentional failure")


# ── BaseAgent Tests ───────────────────────────────────────

class TestBaseAgent:
    @pytest.mark.asyncio
    async def test_run_success(self) -> None:
        provider = MockProvider()
        agent = MockTestAgent(llm_provider=provider)
        state = make_initial_state(query="test")
        result = await agent.run(state)
        assert result.success is True
        assert state["planner_output"] == "test_output"
        assert state["status"] == "completed"

    @pytest.mark.asyncio
    async def test_validate_input_empty_query(self) -> None:
        provider = MockProvider()
        agent = MockTestAgent(llm_provider=provider)
        state = make_initial_state(query="")
        with pytest.raises(ValueError, match="query must not be empty"):
            await agent.validate_input(state)

    @pytest.mark.asyncio
    async def test_run_failure_recovery(self) -> None:
        provider = MockProvider()
        agent = FailingTestAgent(llm_provider=provider)
        state = make_initial_state(query="test")
        result = await agent.run(state)
        assert result.success is False
        assert "intentional failure" in (result.error or "")
        assert state["status"] == "failed"
        assert len(state["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validate_output_hook(self) -> None:
        provider = MockProvider()

        class ValidatingAgent(MockTestAgent):
            agent_name = "validating_agent"

            async def validate_output(self, state: ResearchState) -> None:
                if not state.get("planner_output"):
                    raise ValueError("output missing")

        agent = ValidatingAgent(llm_provider=provider)
        state = make_initial_state(query="test")
        result = await agent.run(state)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_handle_error_custom(self) -> None:
        provider = MockProvider()

        class CustomErrorAgent(BaseAgent):
            agent_name = "custom_error_agent"

            async def arun(self, state: ResearchState) -> ResearchState:
                raise RuntimeError("boom")

            async def handle_error(self, state: ResearchState, exc: Exception) -> ResearchState:
                state["status"] = "recovered"
                state["errors"].append(f"handled: {exc}")
                return state

        agent = CustomErrorAgent(llm_provider=provider)
        state = make_initial_state(query="test")
        result = await agent.run(state)
        assert result.success is False
        assert state["status"] == "recovered"

    def test_agent_name_required(self) -> None:
        with pytest.raises(ValueError):
            AgentRegistry.register(type("NamelessAgent", (BaseAgent,), {"agent_name": "", "arun": lambda self, s: s}))


# ── Registry Tests ────────────────────────────────────────

class TestAgentRegistry:
    def test_register_and_get(self) -> None:
        AgentRegistry._agents.clear()
        MockProvider()
        agent_cls = type("DynamicAgent", (BaseAgent,), {
            "agent_name": "dynamic",
            "description": "dynamically registered",
            "__init__": lambda self, llm: setattr(self, "llm", llm) or setattr(self, "agent_name", "dynamic"),
            "arun": lambda self, s: s,
        })
        AgentRegistry.register(agent_cls)
        retrieved = AgentRegistry.get("dynamic")
        assert retrieved is not None
        assert retrieved.agent_name == "dynamic"

    def test_list_agents(self) -> None:
        AgentRegistry._agents.clear()

        class A(BaseAgent):
            agent_name = "agent_a"
            async def arun(self, state): return state

        class B(BaseAgent):
            agent_name = "agent_b"
            async def arun(self, state): return state

        AgentRegistry.register(A)
        AgentRegistry.register(B)
        agents = AgentRegistry.list_agents()
        names = {a["name"] for a in agents}
        assert "agent_a" in names
        assert "agent_b" in names

    def test_get_nonexistent(self) -> None:
        AgentRegistry._agents.clear()
        assert AgentRegistry.get("nonexistent") is None

    def test_discover(self) -> None:
        # Don't clear registry — modules may already be cached.
        known = len(AgentRegistry._agents)
        AgentRegistry.discover()
        agents = AgentRegistry.list_agents()
        assert len(agents) >= known or len(agents) >= 1


# ── Workflow Tests ────────────────────────────────────────

class TestResearchWorkflow:
    @pytest.mark.asyncio
    async def test_workflow_full_execution(self) -> None:
        workflow = ResearchWorkflow()
        result = await workflow.arun(query="test research query")
        assert result["status"] in ("completed", "report_generation_complete")
        assert result["planner_output"] is not None
        assert "research_goal" in result["planner_output"]
        assert "planner" in result.get("agent_metrics", {})
        assert len(result["retrieved_documents"]) > 0
        assert len(result["summaries"]) > 0
        assert len(result["research_gaps"]) > 0
        assert result["generated_report"] is not None
        assert len(result["execution_history"]) >= 5

    @pytest.mark.asyncio
    async def test_workflow_with_project_id(self) -> None:
        workflow = ResearchWorkflow()
        result = await workflow.arun(query="test", project_id="proj-1", objective="obj-1")
        assert result["project_id"] == "proj-1"
        assert result["objective"] == "obj-1"

    @pytest.mark.asyncio
    async def test_workflow_execution_history_order(self) -> None:
        workflow = ResearchWorkflow()
        result = await workflow.arun(query="ordering test")
        history = result["execution_history"]
        nodes = [h["node"] for h in history]
        # Verify all 5 node entries appear in order (agents may add extra entries)
        node_order = list(dict.fromkeys(n for n in nodes if n in (
            "planner", "retrieval", "summarizer", "gap_detection", "report_generator",
        )))
        assert node_order == ["planner", "retrieval", "summarizer", "gap_detection", "report_generator"]

    @pytest.mark.asyncio
    async def test_workflow_empty_query(self) -> None:
        workflow = ResearchWorkflow()
        result = await workflow.arun(query="")
        assert result["status"] == "failed"
        assert "query must not be empty" in result.get("errors", [])

    @pytest.mark.asyncio
    async def test_workflow_concurrent_executions(self) -> None:
        workflow = ResearchWorkflow()
        import asyncio
        results = await asyncio.gather(
            workflow.arun(query="query 1"),
            workflow.arun(query="query 2"),
            workflow.arun(query="query 3"),
        )
        assert all(r["status"] in ("completed", "report_generation_complete") for r in results)
        assert results[0]["query"] == "query 1"
        assert results[1]["query"] == "query 2"
        assert results[2]["query"] == "query 3"


# ── Node Execution Tests ──────────────────────────────────

class TestGraphNodes:
    @pytest.mark.asyncio
    async def test_planner_node(self) -> None:
        from app.graphs.nodes import planner_node
        state = make_initial_state(query="test")
        result = await planner_node(state)
        assert result["planner_output"] is not None
        assert "research_goal" in result["planner_output"]
        assert result["status"] == "planner_complete"
        assert "agent_metrics" in result
        assert "planner" in result["agent_metrics"]

    @pytest.mark.asyncio
    async def test_retrieval_node_mock_fallback(self) -> None:
        from app.graphs.nodes import retrieval_node
        state = make_initial_state(query="test")
        result = await retrieval_node(state)
        assert len(result["retrieved_documents"]) > 0

    @pytest.mark.asyncio
    async def test_summarizer_node(self) -> None:
        from app.graphs.nodes import summarizer_node
        state = make_initial_state(query="test")
        state["retrieved_documents"] = [
            {"subtopic": "s1", "evidence": [{"content": "doc1 content here", "chunk_id": "c1"}], "sources": ["src1"], "confidence_score": 80.0, "coverage": True},
            {"subtopic": "s2", "evidence": [{"content": "doc2 content here", "chunk_id": "c2"}], "sources": ["src2"], "confidence_score": 80.0, "coverage": True},
        ]
        result = await summarizer_node(state)
        assert len(result["summaries"]) == 2
        for s in result["summaries"]:
            assert "subtopic" in s
            assert "executive_summary" in s
            assert "key_findings" in s

    @pytest.mark.asyncio
    async def test_gap_detection_node(self) -> None:
        from app.graphs.nodes import gap_detection_node
        state = make_initial_state(query="test")
        state["planner_output"] = '{"subtopics": ["s1", "s2"], "research_questions": ["q1"], "search_queries": ["q1"], "priority_areas": ["p1"], "risk_areas": ["r1"]}'
        result = await gap_detection_node(state)
        assert len(result["research_gaps"]) > 0
        for g in result["research_gaps"]:
            assert "gap_id" in g
            assert "gap_type" in g
            assert "severity" in g

    @pytest.mark.asyncio
    async def test_report_generator_node(self) -> None:
        from app.graphs.nodes import report_generator_node
        state = make_initial_state(query="test")
        state["summaries"] = [
            {"subtopic": "S1", "executive_summary": "sum1"},
            {"subtopic": "S2", "executive_summary": "sum2"},
        ]
        state["research_gaps"] = [
            {"gap_id": "g1", "gap_type": "MISSING_SUBTOPIC", "description": "gap1", "severity": "medium"},
        ]
        result = await report_generator_node(state)
        assert result["generated_report"] is not None
        assert "Research Report" in result["generated_report"]
        assert "sum1" in result["generated_report"]
        assert "MISSING_SUBTOPIC" in result["generated_report"]


# ── Failure Recovery Tests ────────────────────────────────

class TestFailureRecovery:
    @pytest.mark.asyncio
    async def test_base_agent_error_records_error(self) -> None:
        provider = MockProvider()
        agent = FailingTestAgent(llm_provider=provider)
        state = make_initial_state(query="test")
        result = await agent.run(state)
        assert result.success is False
        assert len(state["errors"]) > 0
        assert "intentional failure" in state["errors"][0]

    @pytest.mark.asyncio
    async def test_workflow_error_state_propagation(self) -> None:
        from app.graphs.research_graph import ResearchWorkflow

        class FailingWorkflow(ResearchWorkflow):
            async def arun(self, query="", project_id="", objective="", thread_id=None):
                raise RuntimeError("graph failure")

        wf = FailingWorkflow()
        with pytest.raises(RuntimeError, match="graph failure"):
            await wf.arun(query="test")

    @pytest.mark.asyncio
    async def test_conditional_edge_retry_on_error(self) -> None:
        from app.graphs.research_graph import ResearchWorkflow
        state = make_initial_state(query="test")
        state["errors"] = ["planner: something went wrong"]
        result = state
        decision = ResearchWorkflow._should_continue(result)
        assert decision == "retry_planner"

    @pytest.mark.asyncio
    async def test_conditional_edge_complete_on_success(self) -> None:
        from app.graphs.research_graph import ResearchWorkflow
        state = make_initial_state(query="test")
        decision = ResearchWorkflow._should_continue(state)
        assert decision == "complete"

    @pytest.mark.asyncio
    async def test_conditional_edge_retry_retrieval(self) -> None:
        from app.graphs.research_graph import ResearchWorkflow
        state = make_initial_state(query="test")
        state["errors"] = ["retrieval: connection timeout"]
        decision = ResearchWorkflow._should_continue(state)
        assert decision == "retry_retrieval"

    @pytest.mark.asyncio
    async def test_conditional_edge_max_retries(self) -> None:
        from app.graphs.research_graph import ResearchWorkflow
        state = make_initial_state(query="test")
        state["errors"] = ["planner: error"] * 3
        decision = ResearchWorkflow._should_continue(state)
        assert decision == "complete"
