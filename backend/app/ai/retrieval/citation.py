from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Citation:
    source_id: str
    source_title: str
    text: str
    start_pos: int = 0
    end_pos: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class CitationPreserver:
    def __init__(self) -> None:
        self._citations: list[Citation] = []

    def add_citation(self, citation: Citation) -> None:
        self._citations.append(citation)

    def extract_citations(self, text: str) -> list[Citation]:
        import re
        citations = []
        pattern = r'\[@(\w+)\]'
        for match in re.finditer(pattern, text):
            citations.append(Citation(
                source_id=match.group(1),
                source_title="",
                text=match.group(0),
                start_pos=match.start(),
                end_pos=match.end(),
            ))
        return citations

    def preserve_citations(self, text: str, citations: list[Citation]) -> str:
        result = text
        for citation in citations:
            marker = f"[@{citation.source_id}]"
            if marker not in result:
                result += f" {marker}"
        return result

    def get_citation_context(self, text: str, max_context: int = 100) -> list[dict[str, Any]]:
        contexts = []
        for c in self._citations:
            start = max(0, c.start_pos - max_context)
            end = min(len(text), c.end_pos + max_context)
            contexts.append({
                "citation_id": c.source_id,
                "context": text[start:end],
                "source": c.source_title,
            })
        return contexts

    def clear(self) -> None:
        self._citations.clear()
