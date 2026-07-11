from __future__ import annotations

from typing import TYPE_CHECKING

from app.agents.models import AgentMetadata

if TYPE_CHECKING:
    from app.agents.base import BaseAgent


class RegistryError(Exception):
    pass


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, type[BaseAgent]] = {}
        self._instances: dict[str, BaseAgent] = {}

    def register(self, agent_id: str | None = None):
        def decorator(cls: type[BaseAgent]) -> type[BaseAgent]:
            aid = agent_id or getattr(cls, "agent_id", "")
            if not aid:
                raise RegistryError("Agent must define agent_id or pass one to register()")
            if aid in self._agents:
                raise RegistryError(f"Agent '{aid}' already registered")
            self._agents[aid] = cls
            return cls
        return decorator

    def get(self, agent_id: str) -> BaseAgent:
        if agent_id not in self._instances:
            cls = self._agents.get(agent_id)
            if not cls:
                raise RegistryError(f"Agent '{agent_id}' not found. Registered: {list(self._agents.keys())}")
            self._instances[agent_id] = cls()
        return self._instances[agent_id]

    def list_agents(self) -> list[AgentMetadata]:
        return [
            AgentMetadata(
                id=aid,
                name=getattr(cls, "agent_name", aid),
                version=getattr(cls, "version", "1.0"),
            )
            for aid, cls in self._agents.items()
        ]

    def clear_instances(self) -> None:
        self._instances.clear()

    def __contains__(self, agent_id: str) -> bool:
        return agent_id in self._agents
