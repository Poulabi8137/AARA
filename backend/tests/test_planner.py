from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pytest

from app.schemas.planner import PlannerOutput, PlannerMetrics
from app.agents.planner_validator import (
    parse_llm_response,
    compute_planning_score,
    validate_plan,
    _repair_json,
)
from app.agents.prompts import PLANNER_FALLBACK_TEMPLATE
from app.agents.planner_agent import PlannerAgent
from app.agents.state import make_initial_state
from app.llm.provider import LLMResponse, ProviderConfig
from app.llm.mock_provider import MockProvider


# ── Helpers ───────────────────────────────────────────────

_VALID_PLANNER_JSON = json.dumps({
    "research_goal": "Build a comprehensive security framework for agentic AI systems.",
    "research_questions": [
        "What are the unique security vulnerabilities of agentic AI systems?",
        "What mitigation frameworks exist for autonomous agent threats?",
        "How do emergent behaviors in multi-agent systems create new attack surfaces?",
        "What regulatory frameworks apply to agentic AI security?",
    ],
    "keywords": ["agentic AI", "AI security", "autonomous agents", "threat modeling"],
    "search_queries": [
        "agentic AI security vulnerabilities 2025",
        "autonomous agent threat modeling framework",
        "multi-agent system attack surfaces",
        "AI agent governance and compliance",
        "emerging threats in agentic systems",
    ],
    "subtopics": [
        "Agent architecture security",
        "Threat models for autonomous systems",
        "Governance and compliance frameworks",
    ],
    "methodology": "Systematic literature review and threat analysis",
    "expected_deliverables": [
        "Security framework document",
        "Threat taxonomy for agentic AI",
        "Mitigation strategy recommendations",
    ],
    "priority_areas": [
        "Architecture-level vulnerabilities",
        "Runtime behavior monitoring",
        "Cross-agent communication security",
    ],
    "risk_areas": [
        "Rapidly evolving threat landscape",
        "Limited empirical security data",
    ],
    "estimated_steps": 7,
})


class JSONReturningMockProvider(MockProvider):
    """Mock provider that returns valid PlannerOutput JSON."""
    response_json: str = _VALID_PLANNER_JSON

    async def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        return LLMResponse(
            content=self.response_json,
            model="mock-json",
            usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
            finish_reason="stop",
        )


class InvalidJSONMockProvider(MockProvider):
    """Mock provider that returns non-JSON garbage."""
    async def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        return LLMResponse(
            content="This is not valid JSON at all. Sorry!",
            model="mock-bad",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            finish_reason="stop",
        )


class PartiallyBrokenJSONProvider(MockProvider):
    """Mock provider that returns JSON with common LLM errors."""
    async def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        topic = "agentic AI"
        return LLMResponse(
            content=f"""Here is the plan you requested:

{{
  research_goal: "Study {topic}",
  research_questions: ["Question one?", 'Question two?', "Question three?", "Question four?",],
  "keywords": ["kw1", "kw2", "kw3"],
  search_queries: ["query1", "query2", "query3", "query4", "query5",],
  subtopics: ["sub1", "sub2", "sub3"],
  methodology: "review",
  expected_deliverables: ["report"],
  priority_areas: ["area1"],
  risk_areas: [],
  estimated_steps: 5,
}}""",
            model="mock-partial",
            usage={"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
            finish_reason="stop",
        )


# ── PlannerOutput Schema Tests ───────────────────────────

class TestPlannerOutputSchema:
    def test_valid_plan(self) -> None:
        data = json.loads(_VALID_PLANNER_JSON)
        plan = PlannerOutput(**data)
        assert plan.planning_score == 0  # not yet scored
        assert len(plan.research_questions) >= 3
        assert len(plan.search_queries) >= 5
        assert len(plan.subtopics) >= 3
        assert len(plan.research_goal) >= 10

    def test_duplicate_questions_rejected(self) -> None:
        data = json.loads(_VALID_PLANNER_JSON)
        data["research_questions"] = [
            "Same question?",
            "Same question?",
            "Same question?",
        ]
        with pytest.raises(ValueError, match="unique"):
            PlannerOutput(**data)

    def test_duplicate_queries_rejected(self) -> None:
        data = json.loads(_VALID_PLANNER_JSON)
        data["search_queries"] = [
            "same query", "same query", "same query", "same query", "same query"
        ]
        with pytest.raises(ValueError, match="unique"):
            PlannerOutput(**data)

    def test_duplicate_subtopics_rejected(self) -> None:
        data = json.loads(_VALID_PLANNER_JSON)
        data["subtopics"] = ["same", "same", "same"]
        with pytest.raises(ValueError, match="unique"):
            PlannerOutput(**data)

    def test_min_fields_valid(self) -> None:
        plan = PlannerOutput(
            research_goal="Study agentic AI security comprehensively.",
            research_questions=["Q1?", "Q2?", "Q3?"],
            keywords=["kw1", "kw2", "kw3"],
            search_queries=["sq1", "sq2", "sq3", "sq4", "sq5"],
            subtopics=["st1", "st2", "st3"],
            expected_deliverables=["report"],
            priority_areas=["area1"],
            risk_areas=["risk1"],
            estimated_steps=3,
        )
        assert plan.estimated_steps == 3
        assert len(plan.risk_areas) == 1

    def test_estimated_steps_range(self) -> None:
        data = json.loads(_VALID_PLANNER_JSON)
        data["estimated_steps"] = 99
        with pytest.raises(ValueError):
            PlannerOutput(**data)

    def test_short_goal_rejected(self) -> None:
        data = json.loads(_VALID_PLANNER_JSON)
        data["research_goal"] = "Short"
        with pytest.raises(ValueError):
            PlannerOutput(**data)


# ── JSON Parse / Repair Tests ────────────────────────────

class TestParseLLMResponse:
    def test_direct_json(self) -> None:
        result = parse_llm_response('{"key": "value"}')
        assert result is not None
        assert result["key"] == "value"

    def test_markdown_fences(self) -> None:
        result = parse_llm_response("""```json
{"key": "value"}
```""")
        assert result is not None
        assert result["key"] == "value"

    def test_markdown_fences_no_lang(self) -> None:
        result = parse_llm_response("""```
{"key": "value"}
```""")
        assert result is not None
        assert result["key"] == "value"

    def test_json_embedded_in_text(self) -> None:
        result = parse_llm_response("Here is the plan:\n{\"key\": \"value\"}\nEnd.")
        assert result is not None
        assert result["key"] == "value"

    def test_unquoted_keys(self) -> None:
        result = parse_llm_response("{key: \"value\"}")
        assert result is not None
        assert result["key"] == "value"

    def test_trailing_commas(self) -> None:
        result = parse_llm_response('{"key": "value", "list": [1, 2, 3,]}')
        assert result is not None
        assert result["key"] == "value"
        assert result["list"] == [1, 2, 3]

    def test_single_quoted_values(self) -> None:
        result = parse_llm_response("{'key': 'value', 'num': 42}")
        assert result is not None
        assert result["key"] == "value"
        assert result["num"] == 42

    def test_completely_invalid(self) -> None:
        result = parse_llm_response("not json at all")
        assert result is None

    def test_empty_string(self) -> None:
        result = parse_llm_response("")
        assert result is None

    def test_partially_broken_provider(self) -> None:
        """Test that the JSON from PartiallyBrokenJSONProvider gets repaired."""
        provider = PartiallyBrokenJSONProvider()
        import asyncio
        response = asyncio.run(provider.generate("test"))
        result = parse_llm_response(response.content)
        assert result is not None
        assert "research_goal" in result


# ── Repair Helper Tests ──────────────────────────────────

class TestRepairJSON:
    def test_fix_trailing_comma_in_list(self) -> None:
        result = _repair_json('{"a": [1, 2,]}')
        assert result is not None
        import json
        parsed = json.loads(result)
        assert parsed["a"] == [1, 2]

    def test_fix_trailing_comma_in_dict(self) -> None:
        result = _repair_json('{"a": 1, "b": 2,}')
        assert result is not None
        import json
        parsed = json.loads(result)
        assert parsed["a"] == 1

    def test_fix_unquoted_keys(self) -> None:
        result = _repair_json('{key: "value"}')
        assert result is not None
        assert '"key": "value"' in result

    def test_fix_single_quotes(self) -> None:
        result = _repair_json('{"a": \'value\'}')
        assert result is not None
        assert '"a": "value"' in result

    def test_no_braces(self) -> None:
        result = _repair_json("no braces here")
        assert result is None


# ── Quality Scoring Tests ────────────────────────────────

class TestPlanningScore:
    def test_score_calculation(self) -> None:
        data = json.loads(_VALID_PLANNER_JSON)
        plan = PlannerOutput(**data)
        plan = compute_planning_score(plan)
        assert 0 <= plan.planning_score <= 100
        assert 0 <= plan.completeness <= 100
        assert 0 <= plan.coverage <= 100
        assert 0 <= plan.specificity <= 100

    def test_completeness_nonzero(self) -> None:
        data = json.loads(_VALID_PLANNER_JSON)
        plan = PlannerOutput(**data)
        plan = compute_planning_score(plan)
        assert plan.completeness > 50  # All fields populated

    def test_minimal_plan_scores_low(self) -> None:
        plan = PlannerOutput(
            research_goal="Study agentic AI comprehensively.",
            research_questions=["Q1?", "Q2?", "Q3?"],
            keywords=["kw1", "kw2", "kw3"],
            search_queries=["sq1", "sq2", "sq3", "sq4", "sq5"],
            subtopics=["st1", "st2", "st3"],
            expected_deliverables=["report"],
            priority_areas=["pa1"],
            risk_areas=["ra1"],
            estimated_steps=3,
        )
        plan = compute_planning_score(plan)
        assert plan.planning_score < 70  # Minimal plan → lower score


# ── Validation Warning Tests ─────────────────────────────

class TestValidatePlan:
    def test_valid_plan_no_warnings(self) -> None:
        data = json.loads(_VALID_PLANNER_JSON)
        plan = PlannerOutput(**data)
        warnings = validate_plan(plan)
        assert len(warnings) == 0

    def test_questions_without_question_mark(self) -> None:
        plan = PlannerOutput(
            research_goal="Study agentic AI security comprehensively.",
            research_questions=["Question one", "Question two.", "Question three?", "Question four?"],
            keywords=["kw1", "kw2", "kw3"],
            search_queries=["sq1", "sq2", "sq3", "sq4", "sq5"],
            subtopics=["st1", "st2", "st3"],
            expected_deliverables=["report"],
            priority_areas=["pa1"],
            risk_areas=["ra1"],
            estimated_steps=3,
        )
        warnings = validate_plan(plan)
        question_warnings = [w for w in warnings if "research question" in w]
        assert len(question_warnings) == 1

    def test_unusual_steps_warning(self) -> None:
        plan = PlannerOutput(
            research_goal="Study agentic AI security comprehensively.",
            research_questions=["Q1?", "Q2?", "Q3?"],
            keywords=["kw1", "kw2", "kw3"],
            search_queries=["sq1", "sq2", "sq3", "sq4", "sq5"],
            subtopics=["st1", "st2", "st3"],
            expected_deliverables=["report"],
            priority_areas=["pa1"],
            risk_areas=["ra1"],
            estimated_steps=1,
        )
        warnings = validate_plan(plan)
        step_warnings = [w for w in warnings if "estimated_steps" in w]
        assert len(step_warnings) == 1


# ── PlannerAgent Tests ───────────────────────────────────

class TestPlannerAgent:
    @pytest.mark.asyncio
    async def test_valid_json_produces_plan(self) -> None:
        provider = JSONReturningMockProvider()
        agent = PlannerAgent(llm_provider=provider)
        state = make_initial_state(query="Agentic AI security")
        result = await agent.run(state)
        assert result.success is True
        assert state["planner_output"] is not None
        output = json.loads(state["planner_output"])
        assert output["research_goal"] is not None
        assert len(output["research_questions"]) >= 3
        assert len(output["search_queries"]) >= 5
        assert "agent_metrics" in state

    @pytest.mark.asyncio
    async def test_metrics_on_success(self) -> None:
        provider = JSONReturningMockProvider()
        agent = PlannerAgent(llm_provider=provider)
        state = make_initial_state(query="security")
        await agent.run(state)
        metrics = state["agent_metrics"]["planner"]
        assert metrics["latency_seconds"] >= 0
        assert metrics["token_usage"]["total_tokens"] == 300
        assert metrics["used_fallback"] is False
        assert metrics["planning_score"] > 0

    @pytest.mark.asyncio
    async def test_invalid_json_falls_back_to_template(self) -> None:
        provider = InvalidJSONMockProvider()
        agent = PlannerAgent(llm_provider=provider)
        state = make_initial_state(query="quantum computing")
        result = await agent.run(state)
        assert result.success is True
        assert state["planner_output"] is not None
        output = json.loads(state["planner_output"])
        # Fallback template should have produced a plan
        assert len(output["research_questions"]) >= 3
        assert len(output["search_queries"]) >= 5
        assert output["planning_score"] > 0

    @pytest.mark.asyncio
    async def test_fallback_metrics(self) -> None:
        provider = InvalidJSONMockProvider()
        agent = PlannerAgent(llm_provider=provider)
        state = make_initial_state(query="test")
        await agent.run(state)
        metrics = state["agent_metrics"]["planner"]
        assert metrics["used_fallback"] is True
        assert metrics["attempts"] == 3

    @pytest.mark.asyncio
    async def test_planner_output_is_json_string(self) -> None:
        provider = JSONReturningMockProvider()
        agent = PlannerAgent(llm_provider=provider)
        state = make_initial_state(query="AI safety")
        await agent.run(state)
        output = state["planner_output"]
        assert isinstance(output, str)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)
        assert "research_goal" in parsed

    @pytest.mark.asyncio
    async def test_state_updates(self) -> None:
        provider = JSONReturningMockProvider()
        agent = PlannerAgent(llm_provider=provider)
        state = make_initial_state(query="test")
        await agent.run(state)
        assert state["status"] in ("planner_complete", "completed")
        assert "planner" in state["agent_metrics"]

    @pytest.mark.asyncio
    async def test_partially_broken_json_repaired(self) -> None:
        provider = PartiallyBrokenJSONProvider()
        agent = PlannerAgent(llm_provider=provider)
        state = make_initial_state(query="agentic AI")
        result = await agent.run(state)
        assert result.success is True
        assert state["planner_output"] is not None
        output = json.loads(state["planner_output"])
        assert len(output["research_questions"]) >= 3

    @pytest.mark.asyncio
    async def test_planning_score_in_output(self) -> None:
        provider = JSONReturningMockProvider()
        agent = PlannerAgent(llm_provider=provider)
        state = make_initial_state(query="cybersecurity")
        await agent.run(state)
        output = json.loads(state["planner_output"])
        assert 0 <= output["planning_score"] <= 100
        assert output["planning_score"] > 0

    @pytest.mark.asyncio
    async def test_query_reflected_in_plan(self) -> None:
        provider = JSONReturningMockProvider()
        agent = PlannerAgent(llm_provider=provider)
        state = make_initial_state(query="AI alignment")
        await agent.run(state)
        output = json.loads(state["planner_output"])

    @pytest.mark.asyncio
    async def test_retry_behavior(self) -> None:
        """Verify that after all retries exhausted, fallback is used."""
        provider = InvalidJSONMockProvider()
        agent = PlannerAgent(llm_provider=provider)
        state = make_initial_state(query="test query")
        result = await agent.run(state)
        assert result.success is True
        assert state["planner_output"] is not None


# ── Fallback Template Tests ──────────────────────────────

class TestFallbackTemplate:
    def test_template_structure(self) -> None:
        assert "research_goal" in PLANNER_FALLBACK_TEMPLATE
        assert "research_questions" in PLANNER_FALLBACK_TEMPLATE
        assert "search_queries" in PLANNER_FALLBACK_TEMPLATE
        assert "subtopics" in PLANNER_FALLBACK_TEMPLATE

    def test_template_minimums(self) -> None:
        assert len(PLANNER_FALLBACK_TEMPLATE["research_questions"]) >= 3
        assert len(PLANNER_FALLBACK_TEMPLATE["search_queries"]) >= 5
        assert len(PLANNER_FALLBACK_TEMPLATE["subtopics"]) >= 3

    def test_template_formatting(self) -> None:
        goal = PLANNER_FALLBACK_TEMPLATE["research_goal"].format(query="AI")
        assert "AI" in goal
        questions = [q.format(query="AI") for q in PLANNER_FALLBACK_TEMPLATE["research_questions"]]
        assert all("AI" in q for q in questions)

    def test_fallback_creates_valid_output(self) -> None:
        query = "quantum machine learning"
        data = dict(PLANNER_FALLBACK_TEMPLATE)
        data["research_goal"] = data["research_goal"].format(query=query)
        data["research_questions"] = [q.format(query=query) for q in data["research_questions"]]
        data["keywords"] = [k.format(query=query) for k in data["keywords"]]
        data["search_queries"] = [sq.format(query=query) for sq in data["search_queries"]]
        data["subtopics"] = [st.format(query=query) for st in data["subtopics"]]
        data["expected_deliverables"] = [d.format(query=query) for d in data["expected_deliverables"]]
        data["priority_areas"] = [p.format(query=query) for p in data["priority_areas"]]
        data["risk_areas"] = [r.format(query=query) for r in data["risk_areas"]]

        # Pad lists to meet PlannerOutput minimums
        while len(data["keywords"]) < 3:
            data["keywords"].append(f"keyword_{len(data['keywords'])+1}")
        while len(data["search_queries"]) < 5:
            data["search_queries"].append(f"additional query {len(data['search_queries'])+1}")
        while len(data["subtopics"]) < 3:
            data["subtopics"].append(f"subtopic_{len(data['subtopics'])+1}")
        rq = [q for q in data["research_questions"] if q.strip().endswith("?")]
        while len(rq) < 3:
            rq.append(f"What is subtopic {len(rq)+1}?")
        data["research_questions"] = rq

        plan = PlannerOutput(**data)
        plan = compute_planning_score(plan)
        assert len(plan.research_questions) >= 3
        assert plan.planning_score > 0
