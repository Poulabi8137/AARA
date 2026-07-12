from __future__ import annotations

import json
import time
from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry
from app.agents.state import ResearchState
from app.agents.paper_authoring_prompts import (
    PAPER_AUTHOR_SYSTEM_PROMPT,
    PAPER_AUTHOR_USER_PROMPT_TEMPLATE,
    SECTION_REWRITE_PROMPT,
    SECTION_EXPAND_PROMPT,
    SECTION_CONDENSE_PROMPT,
    ACADEMIC_TONE_IMPROVE_PROMPT,
    CITATION_INTEGRATION_PROMPT,
    TECHNICAL_DEPTH_PROMPT,
    IEEE_TEMPLATE_SECTIONS,
)
from app.core.logging import get_logger

logger = get_logger("agents.paper_author")


@AgentRegistry.register
class PaperAuthorAgent(BaseAgent):
    agent_name = "paper_author_agent"
    description = "Generates complete IEEE-style research paper drafts from proposals"
    requires_human_approval = False

    async def arun(self, state: ResearchState) -> ResearchState:
        start = time.monotonic()
        proposal = state.get("proposal", {})
        query = state.get("query", "")

        if not proposal or not isinstance(proposal, dict):
            logger.warning("no proposal available, using fallback")
            paper = self._fallback_paper(query)
        else:
            paper = await self._generate_paper(
                proposal, state.get("base_paper_context", "")
            )

        state["paper_draft"] = paper
        state["status"] = "paper_generated"
        state["agent_metrics"]["paper_author_agent"] = {
            "title": paper.get("title", ""),
            "section_count": len(paper.get("sections", [])),
            "reference_count": len(paper.get("references", [])),
            "latency_seconds": round(time.monotonic() - start, 3),
        }

        history = state.get("execution_history", [])
        history.append(
            {
                "node": "paper_author_agent",
                "timestamp": state.get("timestamp"),
                "status": "paper_generated",
                "paper_title": paper.get("title", ""),
            }
        )
        state["execution_history"] = history

        logger.info(
            "paper generation complete",
            extra={
                "title": paper.get("title", ""),
                "sections": len(paper.get("sections", [])),
            },
        )
        return state

    async def _generate_paper(
        self, proposal: dict[str, Any], base_paper_context: str
    ) -> dict[str, Any]:
        prompt = PAPER_AUTHOR_USER_PROMPT_TEMPLATE.format(
            proposed_title=proposal.get("proposed_title", "Research Paper"),
            problem_statement=proposal.get("problem_statement", ""),
            motivation=proposal.get("motivation", ""),
            research_questions="\n".join(
                f"- {q}" for q in proposal.get("research_questions", [])
            ),
            hypothesis=proposal.get("hypothesis", ""),
            objectives="\n".join(f"- {o}" for o in proposal.get("objectives", [])),
            expected_contributions="\n".join(
                f"- {c}" for c in proposal.get("expected_contributions", [])
            ),
            proposed_methodology=proposal.get("proposed_methodology", ""),
            evaluation_strategy=proposal.get("evaluation_strategy", ""),
            keywords=", ".join(proposal.get("keywords", [])),
            base_paper_context=base_paper_context or "No base paper provided.",
        )
        try:
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt=PAPER_AUTHOR_SYSTEM_PROMPT,
            )
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
                raw = raw.rsplit("\n```", 1)[0]
            return json.loads(raw)
        except Exception as exc:
            logger.warning(
                "LLM paper generation failed, using template", extra={"error": str(exc)}
            )
            return self._template_paper(proposal)

    async def rewrite_section(self, section_title: str, content: str) -> str | None:
        prompt = SECTION_REWRITE_PROMPT.format(
            section_title=section_title, content=content
        )
        try:
            response = await self.llm.generate(prompt=prompt)
            return response.content.strip()
        except Exception as exc:
            logger.warning("section rewrite failed", extra={"error": str(exc)})
            return None

    async def expand_section(self, section_title: str, content: str) -> str | None:
        prompt = SECTION_EXPAND_PROMPT.format(
            section_title=section_title, content=content
        )
        try:
            response = await self.llm.generate(prompt=prompt)
            return response.content.strip()
        except Exception as exc:
            logger.warning("section expand failed", extra={"error": str(exc)})
            return None

    async def condense_section(self, section_title: str, content: str) -> str | None:
        prompt = SECTION_CONDENSE_PROMPT.format(
            section_title=section_title, content=content
        )
        try:
            response = await self.llm.generate(prompt=prompt)
            return response.content.strip()
        except Exception as exc:
            logger.warning("section condense failed", extra={"error": str(exc)})
            return None

    async def improve_tone(self, section_title: str, content: str) -> str | None:
        prompt = ACADEMIC_TONE_IMPROVE_PROMPT.format(
            section_title=section_title, content=content
        )
        try:
            response = await self.llm.generate(prompt=prompt)
            return response.content.strip()
        except Exception as exc:
            logger.warning("tone improvement failed", extra={"error": str(exc)})
            return None

    async def add_citations(
        self, section_title: str, content: str, citations_text: str
    ) -> str | None:
        prompt = CITATION_INTEGRATION_PROMPT.format(
            section_title=section_title, content=content, citations_text=citations_text
        )
        try:
            response = await self.llm.generate(prompt=prompt)
            return response.content.strip()
        except Exception as exc:
            logger.warning("citation integration failed", extra={"error": str(exc)})
            return None

    async def improve_depth(self, section_title: str, content: str) -> str | None:
        prompt = TECHNICAL_DEPTH_PROMPT.format(
            section_title=section_title, content=content
        )
        try:
            response = await self.llm.generate(prompt=prompt)
            return response.content.strip()
        except Exception as exc:
            logger.warning("depth improvement failed", extra={"error": str(exc)})
            return None

    def _template_paper(self, proposal: dict[str, Any]) -> dict[str, Any]:
        title = proposal.get("proposed_title", "Research Paper")
        sections = []
        for sec in IEEE_TEMPLATE_SECTIONS:
            content = self._template_section_content(sec["title"], proposal)
            sections.append(
                {
                    "section_number": sec["number"],
                    "section_title": sec["title"],
                    "content": content,
                }
            )
        return {
            "title": title,
            "abstract": f"This paper addresses {title.lower()}. "
            f"We propose a novel approach to address the research gap identified in the literature. "
            f"Our methodology builds on existing work while introducing key innovations. "
            f"Expected results demonstrate the effectiveness of the proposed approach.",
            "keywords": proposal.get(
                "keywords", ["research", "methodology", "analysis"]
            ),
            "sections": sections,
            "references": [
                {
                    "citation_key": "[1]",
                    "authors": "Placeholder, A.",
                    "title": "Seminal Work in the Field",
                    "year": 2023,
                    "journal": "IEEE Transactions",
                    "doi": None,
                },
                {
                    "citation_key": "[2]",
                    "authors": "Researcher, B.",
                    "title": "Recent Advances",
                    "year": 2024,
                    "journal": "Conference Proceedings",
                    "doi": None,
                },
            ],
        }

    def _template_section_content(
        self, section_title: str, proposal: dict[str, Any]
    ) -> str:
        templates = {
            "Introduction": (
                f"The field of {proposal.get('key_domain', 'research')} has seen significant advances in recent years. "
                f"However, {proposal.get('problem_statement', 'a critical research gap remains')}.\n\n"
                f"This paper addresses this gap by {proposal.get('proposed_methodology', 'proposing a novel approach')}.\n\n"
                f"The remainder of this paper is organized as follows. Section II reviews related work. "
                f"Section III formulates the problem. Section IV presents our proposed solution. "
                f"Section V describes the methodology. Section VI details experimental design. "
                f"Section VII discusses expected results. Section VIII concludes the paper."
            ),
            "Related Work": (
                "Several studies have investigated related problems in this domain. "
                "Previous work by [1] established foundational approaches. "
                "More recently, [2] extended these methods to address specific challenges.\n\n"
                "Table I summarizes key differences between existing approaches and our proposed method.\n\n"
                "[Table I: Comparison of existing approaches with proposed method]"
            ),
            "Problem Statement": (
                f"Despite progress in the field, several challenges remain unaddressed. "
                f"The core problem can be stated as follows:\n\n"
                f"{proposal.get('problem_statement', 'Problem definition')}\n\n"
                f"Specifically, we address the following research questions:\n"
                + "\n".join(
                    f"• {q}" for q in proposal.get("research_questions", [])[:3]
                )
            ),
            "Research Gap": (
                "Through our literature analysis, we identify the following key research gaps:\n\n"
                "• Gap 1: Existing methods do not adequately address [specific issue]\n"
                "• Gap 2: Limited work exists on [specific aspect]\n"
                "• Gap 3: Current evaluation frameworks lack [specific criteria]\n\n"
                "Addressing these gaps motivates our proposed approach."
            ),
            "Proposed Solution": (
                "We propose a novel solution that addresses the identified research gaps. "
                "Figure 1 provides an overview of the proposed approach.\n\n"
                "[Figure 1: Overview of the proposed solution architecture]\n\n"
                "The key innovations of our approach include:\n"
                + "\n".join(
                    f"• {c}" for c in proposal.get("expected_contributions", [])[:3]
                )
            ),
            "System Architecture": (
                "The proposed system architecture consists of several interconnected components. "
                "Figure 2 illustrates the complete architecture.\n\n"
                "[Figure 2: System architecture diagram]\n\n"
                "The main components include:\n"
                "• Component 1: Description of component 1\n"
                "• Component 2: Description of component 2\n"
                "• Component 3: Description of component 3\n\n"
                "Each component interfaces through well-defined APIs, enabling modular development and testing."
            ),
            "Methodology": (
                "Our methodology follows a systematic approach to address the research problem. "
                "The process consists of the following phases:\n\n"
                "Phase 1: Data collection and preprocessing\n"
                "Phase 2: Model design and implementation\n"
                "Phase 3: Training and validation\n"
                "Phase 4: Evaluation and analysis\n\n"
                "Algorithm 1 outlines the core procedure.\n\n"
                "[Algorithm 1: Core procedure of the proposed method]"
            ),
            "Algorithm": (
                f"We present the core algorithm of our proposed approach. "
                f"The algorithm operates as follows:\n\n"
                f"Algorithm 1: Proposed Algorithm\n"
                f"Input: {proposal.get('key_domain', 'input data')}\n"
                f"Output: Results\n\n"
                f"1: Initialize parameters\n"
                f"2: Preprocess input data\n"
                f"3: For each iteration:\n"
                f"4:   Compute intermediate representation\n"
                f"5:   Apply transformation function\n"
                f"6:   Update model parameters\n"
                f"7: End For\n"
                f"8: Return final output\n\n"
                f"The algorithm has a time complexity of O(n) and space complexity of O(n)."
            ),
            "Mathematical Model": (
                "We formulate the problem mathematically as follows:\n\n"
                "[Equation 1: Problem formulation]\n\n"
                "Let X be the input space and Y be the output space. "
                "Our objective function is defined as:\n\n"
                "[Equation 2: Objective function]\n\n"
                "We optimize this objective subject to the following constraints:\n\n"
                "[Equation 3: Constraints]\n\n"
                "The optimization problem is solved using stochastic gradient descent with learning rate decay."
            ),
            "Experimental Design": (
                "We design comprehensive experiments to evaluate the proposed approach. "
                "Table II summarizes the experimental setup.\n\n"
                "[Table II: Experimental setup and parameters]\n\n"
                "Datasets: We plan to evaluate on standard benchmark datasets in the domain.\n"
                "Metrics: Accuracy, precision, recall, F1-score, and computational efficiency.\n"
                "Baselines: Comparison with state-of-the-art methods [1], [2].\n\n"
                "All experiments will be conducted on a system with [specifications] using cross-validation."
            ),
            "Expected Results": (
                "Based on our theoretical analysis, we expect the proposed approach to outperform existing methods. "
                "Figure 3 shows the expected performance comparison.\n\n"
                "[Figure 3: Expected performance comparison]\n\n"
                "(Expected) The proposed method achieves:\n"
                "• Accuracy: ~95% on benchmark datasets\n"
                "• Processing time: 40% faster than baseline\n"
                "• Robustness: Maintains performance under noisy conditions\n\n"
                "Note: These are projected results based on theoretical analysis and preliminary experiments."
            ),
            "Discussion": (
                "Our analysis reveals several important insights. First, the proposed approach effectively addresses the identified research gap. "
                "Second, the experimental results validate our hypothesis that [key hypothesis]. "
                "Third, comparison with existing methods demonstrates clear advantages.\n\n"
                "However, certain limitations should be noted:\n"
                "• The approach may require significant computational resources\n"
                "• Generalization to diverse domains requires further validation\n"
                "• Long-term stability needs additional investigation"
            ),
            "Threats to Validity": (
                "We identify the following threats to the validity of our findings:\n\n"
                "Internal Validity: The experimental setup may introduce confounding variables. "
                "We mitigate this through careful experimental design and multiple trials.\n\n"
                "External Validity: The generalizability of our results may be limited by the choice of datasets. "
                "Future work should evaluate on additional domains.\n\n"
                "Construct Validity: The choice of evaluation metrics may not capture all aspects of performance. "
                "We use multiple complementary metrics to address this."
            ),
            "Future Work": (
                f"Several directions for future research emerge from this work:\n\n"
                f"{proposal.get('future_scope', '')}\n\n"
                f"Specifically, we plan to:\n"
                f"1. Extend the approach to related problem domains\n"
                f"2. Integrate complementary techniques for improved performance\n"
                f"3. Deploy and validate in production environments\n"
                f"4. Investigate theoretical properties of the proposed method"
            ),
            "Conclusion": (
                f"In this paper, we presented a novel approach to {proposal.get('proposed_title', 'the research problem')}. "
                f"Our methodology addresses key limitations of existing approaches. "
                f"The expected results demonstrate the effectiveness of our proposed solution.\n\n"
                f"Key contributions include:\n"
                + "\n".join(
                    f"• {c}" for c in proposal.get("expected_contributions", [])[:3]
                )
                + "\n\nOur work opens several avenues for future research in this domain."
            ),
        }
        return templates.get(
            section_title,
            f"Content for {section_title} section. [Figure/Tables/Equations to be added].",
        )

    def _fallback_paper(self, query: str) -> dict[str, Any]:
        return {
            "title": f"Research on {query[:100]}",
            "abstract": f"This paper investigates {query[:200]}.",
            "keywords": query.split()[:5],
            "sections": [
                {
                    "section_number": i,
                    "section_title": s["title"],
                    "content": f"Content for {s['title']}.",
                }
                for i, s in enumerate(IEEE_TEMPLATE_SECTIONS, 1)
            ],
            "references": [],
        }
