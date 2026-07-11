from __future__ import annotations

from typing import Any


class WorkspaceMemory:
    def __init__(self, workspace_id: str) -> None:
        self.workspace_id = workspace_id
        self._store: dict[str, Any] = {}
        self._papers: list[dict[str, Any]] = []
        self._analyses: list[dict[str, Any]] = []

    async def store(self, key: str, value: Any) -> None:
        self._store[key] = value

    async def retrieve(self, key: str) -> Any | None:
        return self._store.get(key)

    async def add_paper(self, paper: dict[str, Any]) -> None:
        self._papers.append(paper)

    async def get_papers(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        return self._papers[offset:offset + limit]

    async def add_analysis(self, analysis: dict[str, Any]) -> None:
        self._analyses.append(analysis)

    async def get_analyses(
        self, analysis_type: str | None = None
    ) -> list[dict[str, Any]]:
        if analysis_type:
            return [a for a in self._analyses if a.get("type") == analysis_type]
        return self._analyses.copy()

    async def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    async def clear(self) -> None:
        self._store.clear()
        self._papers.clear()
        self._analyses.clear()

    async def snapshot(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "store": self._store.copy(),
            "papers": self._papers.copy(),
            "analyses": self._analyses.copy(),
        }
