from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.models import (
    AgentContext,
    AgentOutput,
    AgentStep,
    ExecutionPlan,
)


class PlanningAgent(BaseAgent):
    agent_id: str = "planner"
    agent_name: str = "Planning Agent"
    version: str = "1.0"
    max_retries: int = 2
    timeout_seconds: int = 30

    async def execute(self, context: AgentContext) -> AgentOutput:
        query = context.input.get("query", "")
        workspace_id = context.input.get("workspace_id", "")

        decomposition = self._decompose_query(query)

        steps = self._build_steps(query, decomposition, workspace_id)

        estimated_tokens = self._estimate_tokens(query)
        search_volume = self._estimate_search_volume(query)

        estimated_cost = {
            "total_tokens": float(estimated_tokens * 5),
            "search_calls": float(search_volume),
            "llm_calls": float(len(steps)),
        }

        plan = ExecutionPlan(
            steps=steps,
            estimated_cost=estimated_cost,
            requires_approval=["research", "analysis", "idea_gen", "writing"],
        )

        return AgentOutput(
            agent_id=self.agent_id,
            workflow_id=context.workflow_id,
            output={"plan": plan, "decomposition": decomposition},
            summary=f"Generated execution plan with {len(steps)} steps",
            duration_ms=0,
        )

    async def validate_output(self, output: AgentOutput) -> bool:
        plan = output.output.get("plan")
        if not isinstance(plan, ExecutionPlan):
            return False
        if not plan.steps:
            return False
        step_ids = {s.agent_id for s in plan.steps}
        required_ids = {"research", "analysis", "idea_gen", "writing", "review"}
        return required_ids.issubset(step_ids)

    def _build_steps(
        self, query: str, decomposition: dict[str, Any], workspace_id: str,
    ) -> list[AgentStep]:
        concepts = decomposition.get("key_concepts", [])
        search_terms = decomposition.get("search_terms", [])
        directions = decomposition.get("research_directions", [])

        research_step = AgentStep(
            agent_id="research",
            input={
                "query": query,
                "workspace_id": workspace_id,
                "key_concepts": concepts,
                "search_terms": search_terms,
                "directions": directions,
            },
            depends_on=[],
            requires_approval=True,
            priority=1,
        )

        analysis_step = AgentStep(
            agent_id="analysis",
            input={
                "query": query,
                "workspace_id": workspace_id,
                "key_concepts": concepts,
            },
            depends_on=["research"],
            requires_approval=True,
            priority=2,
        )

        idea_gen_step = AgentStep(
            agent_id="idea_gen",
            input={
                "query": query,
                "workspace_id": workspace_id,
            },
            depends_on=["analysis"],
            requires_approval=True,
            priority=3,
        )

        writing_step = AgentStep(
            agent_id="writing",
            input={
                "query": query,
                "workspace_id": workspace_id,
            },
            depends_on=["idea_gen"],
            requires_approval=True,
            priority=4,
        )

        review_step = AgentStep(
            agent_id="review",
            input={
                "query": query,
                "workspace_id": workspace_id,
            },
            depends_on=["writing"],
            requires_approval=False,
            priority=5,
        )

        return [research_step, analysis_step, idea_gen_step, writing_step, review_step]

    def _decompose_query(self, query: str) -> dict[str, Any]:
        words = query.lower().split()
        key_concepts = [w for w in words if len(w) > 3]

        search_terms = [query.strip()]
        if len(query) > 100:
            clauses = query.replace("?", ".").split(".")
            search_terms = [c.strip() for c in clauses if len(c.strip()) > 10]

        research_directions = []
        if len(key_concepts) >= 2:
            research_directions.append(f"Relationship between {key_concepts[0]} and {key_concepts[1]}")  # noqa: E501
        if key_concepts:
            research_directions.append(f"Recent advances in {key_concepts[0]}")
        research_directions.append(f"Comprehensive survey of {query[:50]}...")

        return {
            "key_concepts": key_concepts,
            "search_terms": search_terms,
            "research_directions": research_directions,
            "original_query": query,
        }

    def _estimate_search_volume(self, query: str) -> int:
        words = len(query.split())
        if words <= 5:
            return 2
        if words <= 15:
            return 4
        return 6
