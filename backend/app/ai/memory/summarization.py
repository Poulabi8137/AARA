from __future__ import annotations

from typing import Any


class MemorySummarizer:
    def __init__(self, max_summary_length: int = 500) -> None:
        self._max_length = max_summary_length

    async def summarize_session(self, memory: dict[str, Any]) -> str:
        store = memory.get("store", {})
        context = memory.get("context_stack", [])
        summary = f"Session has {len(store)} stored keys, {len(context)} context entries"
        return summary[:self._max_length]

    async def summarize_workspace(self, memory: dict[str, Any]) -> str:
        store = memory.get("store", {})
        papers = memory.get("papers", [])
        analyses = memory.get("analyses", [])
        summary = (
            f"Workspace: {len(store)} stored keys, "
            f"{len(papers)} papers, {len(analyses)} analyses"
        )
        return summary[:self._max_length]

    async def generate_summary(self, data: dict[str, Any], context: str = "") -> str:
        if context == "session":
            return await self.summarize_session(data)
        elif context == "workspace":
            return await self.summarize_workspace(data)
        return f"Memory snapshot: {len(data)} top-level keys"
