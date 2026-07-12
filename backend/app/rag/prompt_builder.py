from __future__ import annotations


from app.core.logging import get_logger
from app.rag.models import RAGContext, SearchIntent

logger = get_logger("rag.prompt_builder")

_SYSTEM_TEMPLATES: dict[str, str] = {
    "default": (
        "You are an AI research assistant. Answer the user's question based on the provided context.\n"
        "Use only the information in the context to answer. If the context does not contain enough "
        "information, state that explicitly.\n"
        "Cite sources where appropriate."
    ),
    "factual": (
        "You are a precise research assistant. Provide accurate, evidence-based answers.\n"
        "Support claims with specific citations from the context.\n"
        "If the evidence is insufficient, clearly indicate the limitation."
    ),
    "exploratory": (
        "You are a research exploration assistant. Synthesize information from multiple sources "
        "to provide a comprehensive overview of the topic.\n"
        "Highlight key themes, patterns, and connections across the evidence.\n"
        "Identify areas of consensus and disagreement in the literature."
    ),
    "comparative": (
        "You are a comparative analysis assistant. Compare and contrast the approaches, "
        "findings, or methodologies described in the context.\n"
        "Present similarities and differences clearly, citing specific sources.\n"
        "Provide a balanced assessment of strengths and limitations."
    ),
    "methodological": (
        "You are a methodology analysis assistant. Focus on research methods, techniques, "
        "and approaches described in the context.\n"
        "Describe methodologies in detail, including their rationale, implementation, "
        "and reported effectiveness.\n"
        "Compare methodological choices across sources."
    ),
    "critical": (
        "You are a critical analysis assistant. Evaluate the evidence from multiple "
        "perspectives, noting limitations, biases, and gaps.\n"
        "Identify methodological concerns, conflicting findings, and areas requiring "
        "further investigation.\n"
        "Maintain a constructive but rigorous analytical stance."
    ),
    "summarization": (
        "You are a research summarization assistant. Distill the key findings, "
        "contributions, and conclusions from the provided context.\n"
        "Present a concise summary organized by theme or finding.\n"
        "Include citations for each major point."
    ),
}

_USER_TEMPLATE: str = (
    "Context:\n{context}\n\n"
    "Question: {query}\n\n"
    "Instructions:\n"
    "- Answer based on the context above\n"
    "- Cite sources as [Source: title]\n"
    "- If the context is insufficient, say so\n"
    "- Be concise and precise"
)

_CITATION_TEMPLATE: str = (
    "When citing sources, use the format: [Source: Title] or [Source: DOI].\n"
    "Always cite the specific source for each factual claim."
)


class PromptBuilder:
    def __init__(self, templates: dict[str, str] | None = None):
        self._templates: dict[str, str] = {**_SYSTEM_TEMPLATES, **(templates or {})}
        self._user_template = _USER_TEMPLATE
        self._citation_instruction = _CITATION_TEMPLATE

    def add_template(self, name: str, template: str) -> None:
        self._templates[name] = template

    def build_system_prompt(
        self,
        intent: SearchIntent | str = SearchIntent.FACTUAL,
        extra_instructions: str | None = None,
    ) -> str:
        key = intent.value if isinstance(intent, SearchIntent) else intent
        prompt = self._templates.get(key, self._templates["default"])
        if extra_instructions:
            prompt = f"{prompt}\n\n{extra_instructions}"
        return prompt

    def build_user_prompt(
        self,
        query: str,
        context: RAGContext,
        include_citations: bool = True,
    ) -> str:
        context_str = self._format_context(context)
        prompt = self._user_template.format(context=context_str, query=query)
        if include_citations:
            prompt = f"{prompt}\n\n{self._citation_instruction}"
        return prompt

    def build_research_prompt(
        self,
        query: str,
        context: RAGContext,
        research_goal: str | None = None,
    ) -> str:
        context_str = self._format_context(context)
        lines = [
            f"Research Goal: {research_goal}" if research_goal else "",
            "",
            f"Context:\n{context_str}",
            "",
            f"Research Question: {query}",
            "",
            "Provide a thorough, well-structured research response.",
            "Cite all sources using [Source: Title] format.",
        ]
        return "\n".join(line for line in lines if line)

    def _format_context(self, context: RAGContext) -> str:
        sections: list[str] = []
        for i, chunk in enumerate(context.chunks, 1):
            header = f"[{i}]"
            if chunk.citation:
                header = f"{header} Source: {chunk.citation}"
            sections.append(f"{header}\n{chunk.content}")
        return "\n\n".join(sections) if sections else "(no context available)"
