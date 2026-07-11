from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.exceptions import RegistryError


@dataclass
class AgentMetadata:
    agent_id: str
    agent_name: str
    version: str = "1.0"
    description: str = ""
    capabilities: list[str] = field(default_factory=list)


class BaseAgent:
    agent_id: str = ""
    agent_name: str = ""
    __version__: str = "1.0"
    max_retries: int = 3


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, type[BaseAgent]] = {}
        self._instances: dict[str, BaseAgent] = {}
        self._metadata: dict[str, AgentMetadata] = {}

    def register(self, agent_id: str | None = None) -> Any:
        def decorator(cls: type[BaseAgent]) -> type[BaseAgent]:
            aid = agent_id or getattr(cls, "agent_id", None)
            if not aid:
                msg = f"Agent class {cls.__name__} must define agent_id"
                raise RegistryError(msg)
            if aid in self._agents:
                raise RegistryError(f"Agent '{aid}' already registered")
            self._agents[aid] = cls
            self._metadata[aid] = AgentMetadata(
                agent_id=aid,
                agent_name=getattr(cls, "agent_name", aid),
                version=getattr(cls, "__version__", "1.0"),
            )
            return cls
        return decorator

    def get(self, agent_id: str) -> BaseAgent:
        if agent_id not in self._instances:
            cls = self._agents.get(agent_id)
            if not cls:
                raise RegistryError(f"Agent '{agent_id}' not found")
            self._instances[agent_id] = cls()
        return self._instances[agent_id]

    def get_class(self, agent_id: str) -> type[BaseAgent]:
        cls = self._agents.get(agent_id)
        if not cls:
            raise RegistryError(f"Agent '{agent_id}' not found")
        return cls

    def list_agents(self) -> list[AgentMetadata]:
        return list(self._metadata.values())

    def get_metadata(self, agent_id: str) -> AgentMetadata:
        meta = self._metadata.get(agent_id)
        if not meta:
            raise RegistryError(f"Agent '{agent_id}' not found")
        return meta

    def clear_instances(self) -> None:
        self._instances.clear()

    def contains(self, agent_id: str) -> bool:
        return agent_id in self._agents
