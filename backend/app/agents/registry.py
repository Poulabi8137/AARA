from __future__ import annotations


from app.agents.base import BaseAgent
from app.core.logging import get_logger

logger = get_logger("agents.registry")


class AgentRegistry:
    """Global registry for research agents.

    Agents register themselves by name. The registry supports
    dynamic discovery so new agent types can be added without
    modifying orchestration code.
    """

    _agents: dict[str, type[BaseAgent]] = {}

    @classmethod
    def register(cls, agent_cls: type[BaseAgent]) -> type[BaseAgent]:
        """Decorator to register an agent class."""
        name = agent_cls.agent_name
        if not name:
            raise ValueError(f"agent_name not set on {agent_cls.__name__}")
        cls._agents[name] = agent_cls
        logger.info("agent registered", extra={"agent_name": name, "class": agent_cls.__name__})
        return agent_cls

    @classmethod
    def get(cls, name: str) -> type[BaseAgent] | None:
        return cls._agents.get(name)

    @classmethod
    def list_agents(cls) -> list[dict[str, str]]:
        return [
            {
                "name": name,
                "description": getattr(agent_cls, "description", ""),
                "requires_human_approval": getattr(agent_cls, "requires_human_approval", False),
            }
            for name, agent_cls in cls._agents.items()
        ]

    @classmethod
    def discover(cls) -> None:
        """Trigger dynamic discovery by importing known agent modules.

        New agent types can register themselves at import time via
        the @AgentRegistry.register decorator.
        """
        modules = [
            "app.agents.planner_agent",
            "app.agents.retrieval_agent",
            "app.agents.summarizer_agent",
            "app.agents.gap_detection_agent",
            "app.agents.report_generator_agent",
            "app.agents.proposal_agent",
            "app.agents.paper_author_agent",
            "app.agents.quality_review_agent",
            "app.agents.citation_validator_agent",
            "app.agents.evidence_validator_agent",
        ]
        for mod in modules:
            try:
                __import__(mod)
            except ImportError:
                logger.warning("agent module not found, skipping", extra={"agent_module": mod})
