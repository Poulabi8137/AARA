from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry
from app.agents.state import ResearchState
from app.agents.prompts import (
    PLANNER_SYSTEM_PROMPT,
    PLANNER_USER_PROMPT_TEMPLATE,
    PLANNER_FALLBACK_TEMPLATE,
)
from app.agents.planner_validator import (
    parse_llm_response,
    compute_planning_score,
    validate_plan,
)
from app.schemas.planner import PlannerOutput, PlannerMetrics
from app.llm.provider import LLMProvider
from app.core.logging import get_logger

logger = get_logger("agents.planner")


@AgentRegistry.register
class PlannerAgent(BaseAgent):
    """Production-grade planner agent.

    Given a research query, generates a structured research plan using
    an LLM, with JSON repair, validation, scoring, and a guaranteed
    fallback template.
    """

    agent_name = "planner"
    description = "Generates a structured, scored research plan from the user query"
    requires_human_approval = False

    MAX_RETRIES = 3

    def __init__(self, llm_provider: LLMProvider) -> None:
        super().__init__(llm_provider)
        self.metrics = PlannerMetrics()

    async def arun(self, state: ResearchState) -> ResearchState:
        query = state.get("query", "")
        objective = state.get("objective", "") or ""
        project_id = state.get("project_id", "") or ""
        start = time.monotonic()

        plan_data: dict[str, Any] | None = None
        last_error: str | None = None
        repair_attempts = 0
        validation_failures = 0
        used_fallback = False

        # --- Attempt LLM generation with retries ---
        for attempt in range(self.MAX_RETRIES):
            try:
                prompt = PLANNER_USER_PROMPT_TEMPLATE.format(
                    query=query,
                    objective=objective,
                    project_id=project_id,
                )
                response = await self.llm.generate(
                    prompt=prompt,
                    system_prompt=PLANNER_SYSTEM_PROMPT,
                )

                raw = response.content
                self.metrics.token_usage = response.usage or {}

                plan_data = parse_llm_response(raw)
                if plan_data is None:
                    if attempt > 0:
                        repair_attempts += 1
                    logger.warning("planner parse failed", extra={"attempt": attempt + 1})
                    continue

                plan = PlannerOutput(**plan_data)
                plan = compute_planning_score(plan)
                warnings = validate_plan(plan)

                if warnings:
                    validation_failures += len(warnings)
                    logger.info("planner validation warnings", extra={"warnings": warnings})

                self.metrics.validation_failures = validation_failures
                self.metrics.repair_attempts = repair_attempts

                output_dict = plan.model_dump()
                state["planner_output"] = json.dumps(output_dict)
                state["status"] = "planner_complete"

                elapsed = time.monotonic() - start
                self.metrics.latency_seconds = round(elapsed, 3)

                state["agent_metrics"] = {
                    "planner": {
                        "latency_seconds": self.metrics.latency_seconds,
                        "token_usage": self.metrics.token_usage,
                        "validation_failures": self.metrics.validation_failures,
                        "repair_attempts": self.metrics.repair_attempts,
                        "used_fallback": False,
                        "planning_score": plan.planning_score,
                        "completeness": plan.completeness,
                        "coverage": plan.coverage,
                        "specificity": plan.specificity,
                        "attempts": attempt + 1,
                    }
                }

                logger.info("planner succeeded", extra={
                    "query": query[:80],
                    "planning_score": plan.planning_score,
                    "questions": len(plan.research_questions),
                    "queries": len(plan.search_queries),
                    "attempts": attempt + 1,
                })
                return state

            except Exception as exc:
                last_error = str(exc)
                logger.warning("planner attempt failed", extra={
                    "attempt": attempt + 1,
                    "error": last_error,
                })

        # --- Fallback: use template ---
        logger.warning("planner using fallback template", extra={"error": last_error})
        used_fallback = True
        fallback = dict(PLANNER_FALLBACK_TEMPLATE)
        fallback["research_goal"] = fallback["research_goal"].format(query=query)
        fallback["research_questions"] = [q.format(query=query) for q in fallback["research_questions"]]
        fallback["keywords"] = [k.format(query=query) for k in fallback["keywords"]]
        fallback["search_queries"] = [sq.format(query=query) for sq in fallback["search_queries"]]
        fallback["subtopics"] = [st.format(query=query) for st in fallback["subtopics"]]
        fallback["expected_deliverables"] = [d.format(query=query) for d in fallback["expected_deliverables"]]
        fallback["priority_areas"] = [p.format(query=query) for p in fallback["priority_areas"]]
        fallback["risk_areas"] = [r.format(query=query) for r in fallback["risk_areas"]]

        def _safe_plan(data: dict) -> PlannerOutput:
            """Build PlannerOutput with guaranteed minimum fields."""
            kw = [k for k in data.get("keywords", []) if k.strip()]
            while len(kw) < 3:
                kw.append(f"topic_{len(kw)+1}")
            sq = [s for s in data.get("search_queries", []) if s.strip()]
            while len(sq) < 5:
                sq.append(f"{query} related research area {len(sq)+1}")
            st = [s for s in data.get("subtopics", []) if s.strip()]
            while len(st) < 3:
                st.append(f"Area {len(st)+1} of {query}")
            rq = [r for r in data.get("research_questions", []) if r.strip().endswith("?")]
            while len(rq) < 3:
                rq.append(f"What is area {len(rq)+1} of {query}?")
            return PlannerOutput(
                research_goal=data.get("research_goal", f"Research on {query}") or f"Research on {query}",
                research_questions=rq,
                keywords=kw,
                search_queries=sq,
                subtopics=st,
                methodology=data.get("methodology", "literature review") or "literature review",
                expected_deliverables=[d for d in data.get("expected_deliverables", [f"Report on {query}"]) if d.strip()] or [f"Report on {query}"],
                priority_areas=[p for p in data.get("priority_areas", [f"Understanding {query}"]) if p.strip()] or [f"Understanding {query}"],
                risk_areas=[r for r in data.get("risk_areas", []) if r.strip()],
                estimated_steps=data.get("estimated_steps", 5) or 5,
            )

        plan = _safe_plan(fallback)

        plan = compute_planning_score(plan)
        elapsed = time.monotonic() - start
        self.metrics.latency_seconds = round(elapsed, 3)
        self.metrics.used_fallback = True

        state["planner_output"] = json.dumps(plan.model_dump())
        state["status"] = "planner_complete"
        state["agent_metrics"] = {
            "planner": {
                "latency_seconds": self.metrics.latency_seconds,
                "token_usage": self.metrics.token_usage,
                "validation_failures": self.metrics.validation_failures,
                "repair_attempts": self.metrics.repair_attempts,
                "used_fallback": True,
                "planning_score": plan.planning_score,
                "completeness": plan.completeness,
                "coverage": plan.coverage,
                "specificity": plan.specificity,
                "attempts": self.MAX_RETRIES,
                "last_error": last_error,
            }
        }

        logger.info("planner completed with fallback", extra={
            "query": query[:80],
            "planning_score": plan.planning_score,
        })
        return state
