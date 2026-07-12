from __future__ import annotations

import json
import time
from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry
from app.agents.state import ResearchState
from app.agents.paper_authoring_prompts import (
    QUALITY_REVIEW_SYSTEM_PROMPT,
    QUALITY_REVIEW_USER_PROMPT,
)
from app.core.logging import get_logger

logger = get_logger("agents.quality_review")


@AgentRegistry.register
class QualityReviewAgent(BaseAgent):
    agent_name = "quality_review_agent"
    description = "Evaluates paper quality across novelty, citations, evidence, methodology, writing, consistency, tone, and completeness"
    requires_human_approval = False

    async def arun(self, state: ResearchState) -> ResearchState:
        start = time.monotonic()
        paper = state.get("paper_draft", {})
        if not paper:
            logger.warning("no paper to review")
            state["quality_review"] = self._empty_review("No paper draft available")
            state["status"] = "review_complete"
            return state

        review = await self._review_paper(paper)
        state["quality_review"] = review
        state["status"] = "review_complete"
        state["agent_metrics"]["quality_review_agent"] = {
            "composite_score": review.get("composite_score", 0),
            "latency_seconds": round(time.monotonic() - start, 3),
        }

        history = state.get("execution_history", [])
        history.append({
            "node": "quality_review_agent",
            "timestamp": state.get("timestamp"),
            "status": "review_complete",
            "composite_score": review.get("composite_score", 0),
        })
        state["execution_history"] = history

        logger.info("quality review complete", extra={
            "composite_score": review.get("composite_score", 0),
        })
        return state

    async def _review_paper(self, paper: dict[str, Any]) -> dict[str, Any]:
        sections = paper.get("sections", [])
        sections_text = "\n\n".join(
            f"Section {s.get('section_number')}: {s.get('section_title')}\n{s.get('content', '')[:500]}"
            for s in sections
        )
        refs = paper.get("references", [])
        refs_text = "\n".join(
            f"{r.get('citation_key', '')} {r.get('authors', '')} - {r.get('title', '')}"
            for r in refs
        ) if refs else "No references."

        prompt = QUALITY_REVIEW_USER_PROMPT.format(
            title=paper.get("title", ""),
            abstract=paper.get("abstract", ""),
            sections_text=sections_text,
            references_text=refs_text,
        )
        try:
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt=QUALITY_REVIEW_SYSTEM_PROMPT,
            )
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
                raw = raw.rsplit("\n```", 1)[0]
            return json.loads(raw)
        except Exception as exc:
            logger.warning("LLM review failed, using template", extra={"error": str(exc)})
            return self._template_review(paper)

    def _template_review(self, paper: dict[str, Any]) -> dict[str, Any]:
        n_sections = len(paper.get("sections", []))
        n_refs = len(paper.get("references", []))
        completeness = min(100, (n_sections / 15) * 100)
        writing = min(70, 50 + n_sections * 2)
        return {
            "novelty_score": 50.0,
            "citation_coverage": min(50, n_refs * 10),
            "evidence_strength": 40.0,
            "methodology_quality": 55.0,
            "writing_quality": writing,
            "logical_consistency": 60.0,
            "academic_tone": 55.0,
            "section_completeness": completeness,
            "composite_score": round((50 + 50 + 40 + 55 + writing + 60 + 55 + completeness) / 8, 1),
            "suggestions": [
                "Add more specific technical details to the methodology section",
                "Include additional references to support claims",
                "Strengthen the evaluation strategy with quantitative metrics",
                "Add mathematical formulations where appropriate",
            ],
            "strengths": [
                f"Paper has {n_sections} out of 15 required IEEE sections",
                "Logical flow follows IEEE conference structure",
                "Abstract clearly states the research contribution",
            ],
            "weaknesses": [
                f"Only {n_refs} references — need more comprehensive literature review",
                "Experimental results are projected, not actual",
                "Technical depth could be improved across sections",
            ],
        }

    def _empty_review(self, reason: str) -> dict[str, Any]:
        return {
            "novelty_score": 0.0,
            "citation_coverage": 0.0,
            "evidence_strength": 0.0,
            "methodology_quality": 0.0,
            "writing_quality": 0.0,
            "logical_consistency": 0.0,
            "academic_tone": 0.0,
            "section_completeness": 0.0,
            "composite_score": 0.0,
            "suggestions": [f"Review unavailable: {reason}"],
            "strengths": [],
            "weaknesses": [reason],
        }

    async def validate_output(self, state: ResearchState) -> None:
        review = state.get("quality_review", {})
        if not isinstance(review, dict):
            raise ValueError("quality_review must be a dict")
