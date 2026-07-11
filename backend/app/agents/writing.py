from __future__ import annotations

import time
from typing import Any

from app.agents.base import BaseAgent
from app.agents.models import AgentContext, AgentOutput

SECTION_NAMES = [
    "Title/Abstract",
    "Introduction",
    "Related Work",
    "Method",
    "Experiment Design",
    "Expected Results",
    "Discussion",
]


class WritingAgent(BaseAgent):
    agent_id = "writer"
    agent_name = "Writing Agent"
    version = "1.0"
    max_retries = 3
    timeout_seconds = 180

    async def execute(self, context: AgentContext) -> AgentOutput:
        start = time.perf_counter()
        analysis_report: dict[str, Any] = context.input.get("analysis_report", {})
        idea_proposal: dict[str, Any] = context.input.get("idea_proposal", {})
        template: dict[str, Any] = context.input.get("template", {})
        # Real papers forwarded from ResearchAgent/AnalysisAgent
        source_papers: list[dict[str, Any]] = context.input.get("papers", [])

        sections: list[dict[str, Any]] = []
        citations: list[dict[str, Any]] = []

        context_data = {
            "analysis_report": analysis_report,
            "idea_proposal": idea_proposal,
            "template": template,
        }

        for section_name in SECTION_NAMES:
            section = await self.generate_section(section_name, context_data)
            section = await self.insert_citations(section, citations, source_papers)
            sections.append(section)

        sections = await self.refine_draft(sections)

        total_words = sum(
            len(s.get("content", "").split()) for s in sections
        )

        paper_draft: dict[str, Any] = {
            "sections": sections,
            "citations": citations,
            "metadata": {
                "template_used": template.get("name", "default"),
                "word_count": total_words,
                "section_count": len(sections),
            },
        }

        duration = int((time.perf_counter() - start) * 1000)
        return AgentOutput(
            agent_id=self.agent_id,
            workflow_id=context.workflow_id,
            output=paper_draft,
            summary=f"Generated draft with {len(sections)} sections, {total_words} words",
            duration_ms=duration,
        )

    async def generate_section(
        self, section_name: str, context_data: dict[str, Any]
    ) -> dict[str, Any]:
        analysis = context_data.get("analysis_report", {})
        ideas = context_data.get("idea_proposal", {})
        context_data.get("template", {})

        content = self._build_section_content(section_name, analysis, ideas)

        return {
            "heading": section_name,
            "content": content,
            "citations": [],
        }

    async def insert_citations(
        self,
        section: dict[str, Any],
        citations: list[dict[str, Any]],
        source_papers: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        content = section.get("content", "")
        heading = section.get("heading", "").lower()
        inserted_ids: list[str] = []

        # Use real papers from the analysis pipeline when available
        pool = source_papers or []
        if not pool:
            section["citations"] = inserted_ids
            return section

        # Map sections to relevant papers by keyword match in title/abstract
        section_keywords: dict[str, list[str]] = {
            "introduction": ["survey", "overview", "review"],
            "related work": ["related", "prior", "existing"],
            "method": ["method", "approach", "framework", "model"],
            "discussion": ["result", "finding", "analysis", "conclusion"],
        }
        keywords = next(
            (v for k, v in section_keywords.items() if k in heading),
            [],
        )

        matched: list[dict[str, Any]] = []
        for paper in pool:
            title = (paper.get("title") or "").lower()
            abstract = (paper.get("abstract") or "").lower()
            text = f"{title} {abstract}"
            if any(kw in text for kw in keywords) or not keywords:
                matched.append(paper)
            if len(matched) >= 3:
                break

        for paper in matched:
            doi = paper.get("doi") or paper.get("arxiv_id") or paper.get("id", "")
            if not doi:
                continue
            citation_id = f"cit_{len(citations) + 1}"
            title_snippet = (paper.get("title") or doi)[:80]
            citations.append({
                "id": citation_id,
                "doi": doi,
                "text": title_snippet,
                "context": section.get("heading", ""),
            })
            inserted_ids.append(citation_id)

        if inserted_ids:
            content = content.rstrip(".")
            refs = " ".join(f"[@{cid}]" for cid in inserted_ids)
            content = f"{content} {refs}."

        section["content"] = content
        section["citations"] = inserted_ids
        return section

    async def refine_draft(
        self, sections: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        refined: list[dict[str, Any]] = []
        for section in sections:
            content = section.get("content", "")
            content = content.replace("  ", " ")
            content = content.strip()
            if content and not content.endswith("."):
                content += "."
            section["content"] = content
            refined.append(section)
        return refined

    def _build_section_content(
        self,
        section_name: str,
        analysis: dict[str, Any],
        ideas: dict[str, Any],
    ) -> str:
        ideas.get("ideas", [])
        synthesis = ideas.get("synthesis", "")
        title = analysis.get("title", "Research Topic")

        section_templates = {
            "Title/Abstract": (
                f"Title: Advancing Research in {title}\n\n"
                f"Abstract: This paper investigates key research gaps identified in the "
                f"current literature on {title}. {synthesis}"
            ),
            "Introduction": (
                f"The field of {title} has seen significant advances in recent years. "
                f"However, several critical gaps remain unaddressed. This work aims to "
                f"bridge these gaps by proposing novel approaches that build on existing "
                f"foundations."
            ),
            "Related Work": (
                f"Prior research in {title} has established foundational knowledge in "
                f"several key areas. The literature review reveals that while substantial "
                f"progress has been made, there remain opportunities for further investigation "
                f"in underexplored directions."
            ),
            "Method": (
                "We propose a systematic methodology designed to address the research "
                "questions identified in this study. The approach combines quantitative "
                "and qualitative techniques to ensure robust and reproducible results."
            ),
            "Experiment Design": (
                "The experiment is designed to test the hypotheses derived from the "
                "identified research gaps. Data collection will follow a structured "
                "protocol with appropriate controls and validation procedures."
            ),
            "Expected Results": (
                f"We anticipate that the proposed experiments will yield insights that "
                f"significantly advance understanding in {title}. Preliminary analysis "
                f"suggests that the research directions identified are both feasible "
                f"and impactful."
            ),
            "Discussion": (
                f"The findings from this study are expected to contribute to the broader "
                f"understanding of {title}. {synthesis} Future work should build "
                f"on these results to further explore the remaining open questions."
            ),
        }

        return section_templates.get(section_name, f"Section: {section_name}\nContent to be developed.")  # noqa: E501

    async def validate_output(self, output: AgentOutput) -> bool:
        draft = output.output
        if "sections" not in draft or not isinstance(draft["sections"], list):
            return False
        for section in draft["sections"]:
            if not {"heading", "content", "citations"}.issubset(section.keys()):
                return False
        if "citations" not in draft or not isinstance(draft["citations"], list):
            return False
        for cit in draft["citations"]:
            if not {"id", "doi", "text", "context"}.issubset(cit.keys()):
                return False
        if "metadata" not in draft or not isinstance(draft["metadata"], dict):
            return False
        meta = draft["metadata"]
        return {"template_used", "word_count", "section_count"}.issubset(meta.keys())
