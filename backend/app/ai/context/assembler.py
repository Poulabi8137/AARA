from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ai.context.budgeting import TokenBudget
from app.ai.context.compression import ContextCompressor
from app.ai.context.deduplication import SourceDeduplicator


@dataclass
class ContextSection:
    name: str
    content: str
    source: str = ""
    priority: int = 0
    token_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class ContextAssembler:
    def __init__(
        self,
        token_budget: TokenBudget | None = None,
        max_tokens: int = 8000,
    ) -> None:
        self._budget = token_budget or TokenBudget(max_tokens=max_tokens)
        self._deduplicator = SourceDeduplicator()
        self._compressor = ContextCompressor()

    async def assemble(
        self,
        sections: list[ContextSection],
        query: str = "",
    ) -> str:
        sections.sort(key=lambda s: s.priority, reverse=True)

        for section in sections:
            section.token_count = self._estimate_tokens(section.content)

        sections = self._deduplicator.dedup(sections)

        budget_result = self._budget.allocate(sections)
        if budget_result.truncated:
            sections = budget_result.allocated
            compressed = await self._compressor.compress(
                [s.content for s in sections],
            )
            for i, s in enumerate(sections):
                if i < len(compressed):
                    s.content = compressed[i]

        context_parts = []
        for section in sections:
            if section.source:
                context_parts.append(
                    f"[Source: {section.source}]\n{section.content}"
                )
            else:
                context_parts.append(section.content)

        return "\n\n".join(context_parts)

    async def assemble_with_citations(
        self,
        sections: list[ContextSection],
        citations: list[dict[str, Any]],
    ) -> str:
        context = await self.assemble(sections)
        citation_lines = []
        for c in citations:
            citation_lines.append(f"[@{c.get('id', '?')}] {c.get('title', 'Unknown source')}")
        if citation_lines:
            context += "\n\nReferences:\n" + "\n".join(citation_lines)
        return context

    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4
