from __future__ import annotations

from typing import Any


class GlobalMemory:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self._store: dict[str, Any] = {}
        self._prompt_templates: dict[str, str] = {}
        self._execution_patterns: list[dict[str, Any]] = []

    async def save_prompt_template(self, name: str, template: str) -> None:
        self._prompt_templates[name] = template

    async def get_prompt_template(self, name: str) -> str | None:
        return self._prompt_templates.get(name)

    async def delete_prompt_template(self, name: str) -> bool:
        return self._prompt_templates.pop(name, None) is not None

    async def record_execution_pattern(self, agent_id: str, pattern: dict[str, Any]) -> None:
        self._execution_patterns.append({
            "agent_id": agent_id,
            "pattern": pattern,
        })

    async def get_execution_patterns(
        self, agent_id: str | None = None
    ) -> list[dict[str, Any]]:
        if agent_id:
            return [p for p in self._execution_patterns if p.get("agent_id") == agent_id]
        return self._execution_patterns.copy()

    async def store(self, key: str, value: Any) -> None:
        self._store[key] = value

    async def retrieve(self, key: str) -> Any | None:
        return self._store.get(key)

    async def clear(self) -> None:
        self._store.clear()
        self._prompt_templates.clear()
        self._execution_patterns.clear()
