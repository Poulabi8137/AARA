from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ai.context.assembler import ContextSection


class SourceDeduplicator:
    def dedup(
        self, sections: list[ContextSection]
    ) -> list[ContextSection]:
        seen: set[str] = set()
        result: list[ContextSection] = []

        for section in sections:
            key = self._make_key(section)
            if key not in seen:
                seen.add(key)
                result.append(section)

        return result

    def _make_key(self, section: ContextSection) -> str:
        content_hash = hashlib.md5(section.content.encode()).hexdigest()
        return f"{section.source}:{content_hash}"

    def dedup_by_source(
        self, sections: list[ContextSection]
    ) -> dict[str, list[ContextSection]]:
        by_source: dict[str, list[ContextSection]] = {}
        for section in sections:
            by_source.setdefault(section.source, []).append(section)
        return by_source
