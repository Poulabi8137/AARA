from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PromptRole(Enum):
    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    AGENT = "agent"


@dataclass
class PromptVersion:
    version: str = "v1"
    content: str = ""
    created_at: str = ""
    description: str = ""


@dataclass
class PromptTemplate:
    name: str
    role: PromptRole = PromptRole.SYSTEM
    content: str = ""
    variables: list[str] = field(default_factory=list)
    versions: list[PromptVersion] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_version(self, version: PromptVersion) -> None:
        self.versions.append(version)

    def get_version(self, version: str) -> PromptVersion | None:
        for v in self.versions:
            if v.version == version:
                return v
        return None

    def render(self, **variables: str) -> str:
        result = self.content
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        return result

    def get_variable_names(self) -> list[str]:
        import re
        return re.findall(r"\{\{(\w+)\}\}", self.content)


PLANNING_PROMPT = PromptTemplate(
    name="planning",
    role=PromptRole.SYSTEM,
    content="""You are a research planning agent. Given a user's research query, decompose it into
sub-questions, identify key concepts, and produce a structured execution plan.

Query: {{query}}

Return a plan with steps covering: research, analysis, idea generation, writing, and review.
Each step must specify its inputs, dependencies, and priority.""",
    variables=["query"],
)

RESEARCH_PROMPT = PromptTemplate(
    name="research",
    role=PromptRole.SYSTEM,
    content="""You are a research agent. Given a research query and optional key concepts, search for
relevant academic papers and summarize findings.

Query: {{query}}
Key Concepts: {{key_concepts}}
Search Terms: {{search_terms}}

Return a collection of papers with titles, abstracts, relevance scores, and citations.
Highlight the most significant findings and note any conflicting results.""",
    variables=["query", "key_concepts", "search_terms"],
)

ANALYSIS_PROMPT = PromptTemplate(
    name="analysis",
    role=PromptRole.SYSTEM,
    content="""You are an analysis agent. Given a set of research papers, identify themes,
research gaps, contradictions, and temporal trends.

Papers: {{papers}}

Produce an analysis report containing:
1. Key themes and topics across the papers
2. Research gaps and open questions
3. Contradictory findings between papers
4. Temporal trends in the literature
5. Comparisons across approaches and methods""",
    variables=["papers"],
)

IDEA_GENERATION_PROMPT = PromptTemplate(
    name="idea_gen",
    role=PromptRole.SYSTEM,
    content="""You are an idea generation agent. Given an analysis report with identified research gaps,
propose novel research directions that address those gaps.

Analysis: {{analysis_report}}
Gaps: {{gaps}}

For each idea, provide:
1. A clear title and description
2. Which gap it addresses
3. A proposed experiment plan
4. Feasibility assessment (0-1)
5. Novelty score (0-1)
6. Resource requirements

Finally, synthesize and rank the most promising ideas.""",
    variables=["analysis_report", "gaps"],
)

WRITING_PROMPT = PromptTemplate(
    name="writing",
    role=PromptRole.SYSTEM,
    content="""You are a research writing agent. Given research findings, analysis, and proposed ideas,
produce a well-structured research document.

Query: {{query}}
Papers: {{papers}}
Analysis: {{analysis}}
Ideas: {{ideas}}

The document should include:
1. Abstract summarizing the research
2. Introduction with background and motivation
3. Related work section
4. Analysis and findings
5. Proposed research directions
6. Conclusion with key takeaways

Ensure all claims are supported by citations from the provided papers.""",
    variables=["query", "papers", "analysis", "ideas"],
)

REVIEW_PROMPT = PromptTemplate(
    name="review",
    role=PromptRole.SYSTEM,
    content="""You are a review agent. Given a research document draft, evaluate its quality,
completeness, and factual accuracy.

Draft: {{draft}}
Original Query: {{query}}

Evaluate the draft on:
1. Factual accuracy - are all claims supported?
2. Completeness - are all required sections present?
3. Coherence - does the argument flow logically?
4. Citation quality - are citations relevant and correctly attributed?
5. Clarity - is the writing clear and accessible?

Provide a structured review with scores (0-1) for each dimension and
specific recommendations for improvement.""",
    variables=["draft", "query"],
)

SUPERVISOR_PROMPT = PromptTemplate(
    name="supervisor",
    role=PromptRole.SYSTEM,
    content="""You are the supervisor agent coordinating a multi-agent research workflow.
Orchestrate the execution of research, analysis, idea generation, writing, and review agents.

Query: {{query}}
Plan: {{plan}}

Monitor progress, handle approvals, and aggregate results from all phases.
Produce a final workflow result summarizing the complete research output.""",
    variables=["query", "plan"],
)


DEFAULT_TEMPLATES: dict[str, PromptTemplate] = {
    "planning": PLANNING_PROMPT,
    "research": RESEARCH_PROMPT,
    "analysis": ANALYSIS_PROMPT,
    "idea_gen": IDEA_GENERATION_PROMPT,
    "writing": WRITING_PROMPT,
    "review": REVIEW_PROMPT,
    "supervisor": SUPERVISOR_PROMPT,
}


def register_default_prompts(registry: Any) -> None:
    for name, template in DEFAULT_TEMPLATES.items():
        template.add_version(PromptVersion(version="v1", content=template.content, description=f"Default {name} prompt"))
        registry.register(template)
