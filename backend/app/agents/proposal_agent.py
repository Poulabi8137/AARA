from __future__ import annotations

import json
import time
from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry
from app.agents.state import ResearchState
from app.agents.paper_authoring_prompts import (
    PROPOSAL_SYSTEM_PROMPT,
    PROPOSAL_USER_PROMPT_TEMPLATE,
)
from app.core.logging import get_logger

logger = get_logger("agents.proposal")


@AgentRegistry.register
class ProposalAgent(BaseAgent):
    agent_name = "proposal_agent"
    description = "Generates structured research proposals from identified research gaps"
    requires_human_approval = True

    async def arun(self, state: ResearchState) -> ResearchState:
        start = time.monotonic()
        gap = state.get("selected_gap", {})
        query = state.get("query", "")
        objective = state.get("objective", "")
        domain = state.get("domain", "")
        keywords = state.get("keywords", "")
        methodology_preference = state.get("methodology_preference", "")

        gap_desc = gap.get("description", query) if isinstance(gap, dict) else str(gap)
        gap_desc = gap_desc or query

        proposal = await self._generate_proposal(
            gap_description=gap_desc,
            domain=domain or query,
            objective=objective,
            keywords=keywords,
            methodology_preference=methodology_preference,
        )

        state["proposal"] = proposal
        state["status"] = "proposal_complete"
        state["agent_metrics"]["proposal_agent"] = {
            "title": proposal.get("proposed_title", ""),
            "latency_seconds": round(time.monotonic() - start, 3),
        }

        history = state.get("execution_history", [])
        history.append({
            "node": "proposal_agent",
            "timestamp": state.get("timestamp"),
            "status": "proposal_complete",
            "proposal_title": proposal.get("proposed_title", ""),
        })
        state["execution_history"] = history

        logger.info("proposal generation complete", extra={
            "title": proposal.get("proposed_title", ""),
        })
        return state

    async def _generate_proposal(
        self,
        gap_description: str,
        domain: str,
        objective: str,
        keywords: str,
        methodology_preference: str,
    ) -> dict[str, Any]:
        prompt = PROPOSAL_USER_PROMPT_TEMPLATE.format(
            gap_description=gap_description,
            domain=domain,
            objective=objective,
            keywords=keywords,
            methodology_preference=methodology_preference,
        )
        try:
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt=PROPOSAL_SYSTEM_PROMPT,
            )
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
                raw = raw.rsplit("\n```", 1)[0]
            return json.loads(raw)
        except Exception as exc:
            logger.warning("LLM proposal generation failed, using fallback", extra={"error": str(exc)})
            return self._fallback_proposal(gap_description, domain)

    def _fallback_proposal(self, gap: str, domain: str) -> dict[str, Any]:
        return {
            "proposed_title": f"Investigating {gap[:100]}",
            "problem_statement": f"The research gap in {domain} regarding {gap[:150]} requires systematic investigation.",
            "motivation": f"Addressing this gap will advance the field of {domain} and provide practical benefits.",
            "research_questions": [
                f"What is the current state of {gap[:100]}?",
                f"What are the key challenges in addressing {gap[:80]}?",
                f"What novel approaches can be developed for {gap[:80]}?",
            ],
            "hypothesis": f"A systematic approach to {gap[:100]} will yield significant improvements over existing methods.",
            "objectives": [
                f"Analyze the current landscape of {gap[:80]}",
                f"Develop a novel approach for {gap[:80]}",
                "Evaluate the proposed approach through rigorous experimentation",
            ],
            "expected_contributions": [
                f"A comprehensive analysis of {gap[:80]}",
                "A novel methodology for addressing key challenges",
                "Empirical evaluation demonstrating effectiveness",
            ],
            "proposed_methodology": "Literature review, algorithmic development, experimental evaluation, and statistical analysis.",
            "evaluation_strategy": "Quantitative evaluation using standard benchmarks and metrics, with qualitative analysis of results.",
            "future_scope": "Extension to related domains, integration with complementary approaches, and deployment in production environments.",
        }
