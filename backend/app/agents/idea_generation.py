from __future__ import annotations

import time
from typing import Any

from app.agents.base import BaseAgent
from app.agents.models import AgentContext, AgentOutput, ConfidenceScore


class IdeaGenerationAgent(BaseAgent):
    agent_id = "idea_gen"
    agent_name = "Idea Generation Agent"
    version = "2.0"
    max_retries = 2
    timeout_seconds = 90

    async def execute(self, context: AgentContext) -> AgentOutput:
        start = time.perf_counter()
        analysis_report: dict[str, Any] = context.input.get("analysis_report", {})
        gaps: list[dict[str, Any]] = analysis_report.get("research_gaps", [])
        papers: list[dict[str, Any]] = analysis_report.get("papers", [])

        all_ideas: list[dict[str, Any]] = []
        for gap in gaps:
            ideas = await self.generate_ideas(gap)
            for idea in ideas:
                overlap = await self.detect_novelty(idea, papers)
                idea["overlap_score"] = overlap
                idea["overlapping_papers"] = [
                    p.get("id", "")
                    for p in papers
                    if p.get("id", "") in idea.get("overlapping_paper_ids", [])
                ]
            all_ideas.extend(ideas)

        opportunities = await self.generate_opportunities(all_ideas)
        for idea, opp in zip(all_ideas, opportunities, strict=False):
            idea["feasibility"] = opp.get("feasibility", 0.5)
            idea["novelty_score"] = opp.get("novelty_score", 0.5)
            idea["resource_requirements"] = opp.get("resource_requirements", "medium")

        recommendations = await self.generate_recommendations(all_ideas)
        for rec in recommendations:
            for idea in all_ideas:
                if idea.get("title") == rec.get("idea_id"):
                    idea.get("recommendation", {}).update(rec)

        synthesis = self._build_synthesis(all_ideas, gaps)

        avg_novelty = sum(idea.get("overlap_score", 1.0) for idea in all_ideas) / max(len(all_ideas), 1)
        avg_feasibility = sum(idea.get("feasibility", 0.0) for idea in all_ideas) / max(len(all_ideas), 1)
        novelty_support = 1.0 - avg_novelty
        overall_confidence = (novelty_support * 0.5 + avg_feasibility * 0.5)

        idea_proposal: dict[str, Any] = {
            "ideas": all_ideas,
            "recommendations": recommendations,
            "synthesis": synthesis,
        }
        duration = int((time.perf_counter() - start) * 1000)
        return AgentOutput(
            agent_id=self.agent_id,
            workflow_id=context.workflow_id,
            output=idea_proposal,
            summary=f"Generated {len(all_ideas)} ideas across {len(gaps)} gaps",
            duration_ms=duration,
            confidence=ConfidenceScore(
                overall=round(min(overall_confidence, 1.0), 3),
                citation_support=round(novelty_support, 3),
                factual_grounding=round(avg_feasibility, 3),
                reasoning_coherence=round(novelty_support, 3),
            ),
        )

    async def generate_ideas(self, gap: dict[str, Any]) -> list[dict[str, Any]]:
        gap_description = gap.get("description", "")
        gap_area = gap.get("area", "general")
        ideas = [
            {
                "title": f"Investigating {gap_area}: {gap_description[:60]}",
                "description": f"Propose a study addressing {gap_description}",
                "gap_addressed": gap.get("id", ""),
                "overlap_score": 0.0,
                "overlapping_papers": [],
                "experiment_plan": "TBD based on methodology selection",
                "feasibility": 0.0,
                "novelty_score": 0.0,
                "resource_requirements": "medium",
            },
            {
                "title": f"Novel framework for {gap_area}",
                "description": f"Develop a new methodological approach for {gap_description}",
                "gap_addressed": gap.get("id", ""),
                "overlap_score": 0.0,
                "overlapping_papers": [],
                "experiment_plan": "Framework design followed by empirical validation",
                "feasibility": 0.0,
                "novelty_score": 0.0,
                "resource_requirements": "medium",
            },
        ]
        if len(gap_description) > 80:
            ideas.append({
                "title": f"Longitudinal study on {gap_area}",
                "description": f"Track changes over time to understand {gap_description}",
                "gap_addressed": gap.get("id", ""),
                "overlap_score": 0.0,
                "overlapping_papers": [],
                "experiment_plan": "Multi-phase data collection and analysis",
                "feasibility": 0.0,
                "novelty_score": 0.0,
                "resource_requirements": "high",
            })
        return ideas

    async def detect_novelty(
        self, idea: dict[str, Any], papers: list[dict[str, Any]]
    ) -> float:
        idea_title = idea.get("title", "").lower()
        idea_desc = idea.get("description", "").lower()
        idea_tokens = set((idea_title + " " + idea_desc).split())
        overlapping_ids: list[str] = []
        for paper in papers:
            title = paper.get("title", "").lower()
            abstract = paper.get("abstract", "").lower()
            paper_tokens = set((title + " " + abstract).split())
            if len(idea_tokens) > 0 and len(paper_tokens) > 0:
                jaccard = len(idea_tokens & paper_tokens) / len(idea_tokens | paper_tokens)
                if jaccard > 0.15:
                    overlapping_ids.append(paper.get("id", ""))
        idea["overlapping_paper_ids"] = overlapping_ids
        total = len(papers) if papers else 1
        return min(1.0, len(overlapping_ids) / total)

    async def generate_opportunities(
        self, ideas: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        opportunities: list[dict[str, Any]] = []
        for idea in ideas:
            overlap = idea.get("overlap_score", 0.5)
            feasibility = max(0.1, 1.0 - overlap * 0.5)
            novelty_score = max(0.1, 1.0 - overlap)
            if feasibility > 0.7:
                resource = "low"
            elif feasibility > 0.4:
                resource = "medium"
            else:
                resource = "high"
            opportunities.append({
                "feasibility": round(feasibility, 2),
                "novelty_score": round(novelty_score, 2),
                "resource_requirements": resource,
            })
        return opportunities

    async def generate_recommendations(
        self, ideas: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        scored = []
        for idx, idea in enumerate(ideas):
            f = idea.get("feasibility", 0.5)
            n = idea.get("novelty_score", 0.5)
            resource_map = {"low": 1.0, "medium": 0.7, "high": 0.4}
            r = resource_map.get(idea.get("resource_requirements", "medium"), 0.7)
            composite = round(f * 0.4 + n * 0.4 + r * 0.2, 3)
            scored.append((composite, idx, idea))
        scored.sort(key=lambda x: x[0], reverse=True)
        recommendations = []
        for _rank, (composite, idx, idea) in enumerate(scored):
            if composite >= 0.7:
                priority = "high"
            elif composite >= 0.4:
                priority = "medium"
            else:
                priority = "low"
            recommendations.append({
                "idea_id": idea.get("title", f"idea_{idx}"),
                "priority": priority,
                "rationale": (
                    f"Composite score {composite}: "
                    f"feasibility={idea.get('feasibility', 0.5)}, "
                    f"novelty={idea.get('novelty_score', 0.5)}, "
                    f"resources={idea.get('resource_requirements', 'medium')}"
                ),
            })
        return recommendations

    def _build_synthesis(
        self, ideas: list[dict[str, Any]], gaps: list[dict[str, Any]]
    ) -> str:
        gap_areas = ", ".join(g.get("area", "unknown") for g in gaps)
        top = sorted(
            ideas,
            key=lambda i: i.get("feasibility", 0) * 0.4 + i.get("novelty_score", 0) * 0.4,
            reverse=True,
        )[:3]
        top_titles = "; ".join(i.get("title", "") for i in top)
        return (
            f"Generated {len(ideas)} ideas addressing gaps in: {gap_areas}. "
            f"Top opportunities include: {top_titles}. "
            f"Overall direction emphasizes novel methodologies with feasible resource profiles."
        )

    async def validate_output(self, output: AgentOutput) -> bool:
        proposal = output.output
        if "ideas" not in proposal or not isinstance(proposal["ideas"], list):
            return False
        for idea in proposal["ideas"]:
            required = {"title", "description", "gap_addressed", "overlap_score",
                        "overlapping_papers", "experiment_plan", "feasibility",
                        "novelty_score", "resource_requirements"}
            if not required.issubset(idea.keys()):
                return False
        if "recommendations" not in proposal or not isinstance(proposal["recommendations"], list):
            return False
        for rec in proposal["recommendations"]:
            if not {"idea_id", "priority", "rationale"}.issubset(rec.keys()):
                return False
        return not ("synthesis" not in proposal or not isinstance(proposal["synthesis"], str))
