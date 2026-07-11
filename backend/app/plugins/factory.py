from __future__ import annotations

from typing import Any

from app.plugins.agent_registry import AgentRegistry, BaseAgent
from app.plugins.tool_registry import BaseTool, ToolRegistry


class AgentFactory:
    def __init__(self, registry: AgentRegistry) -> None:
        self._registry = registry
        self._pre_hooks: list[Any] = []
        self._post_hooks: list[Any] = []

    def register_pre_hook(self, hook: Any) -> None:
        self._pre_hooks.append(hook)

    def register_post_hook(self, hook: Any) -> None:
        self._post_hooks.append(hook)

    def create(self, agent_id: str) -> BaseAgent:
        for hook in self._pre_hooks:
            hook(agent_id)
        instance = self._registry.get(agent_id)
        for hook in self._post_hooks:
            hook(agent_id, instance)
        return instance

    def create_all(self, agent_ids: list[str]) -> dict[str, BaseAgent]:
        return {aid: self.create(aid) for aid in agent_ids}


class ToolFactory:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def create(self, tool_id: str) -> BaseTool:
        cls = self._registry.get_tool(tool_id)
        return cls()

    def create_all(self, tool_ids: list[str]) -> dict[str, BaseTool]:
        return {tid: self.create(tid) for tid in tool_ids}
