from __future__ import annotations

from app.agents.registry import AgentRegistry

_registry = AgentRegistry()

registry = _registry

from app.agents.analysis import AnalysisAgent  # noqa: E402
from app.agents.idea_generation import IdeaGenerationAgent  # noqa: E402
from app.agents.planning import PlanningAgent  # noqa: E402
from app.agents.research import ResearchAgent  # noqa: E402
from app.agents.review import ReviewAgent  # noqa: E402
from app.agents.supervisor import SupervisorAgent  # noqa: E402
from app.agents.writing import WritingAgent  # noqa: E402

_registry.register("planner")(PlanningAgent)
_registry.register("research")(ResearchAgent)
_registry.register("analysis")(AnalysisAgent)
_registry.register("idea_gen")(IdeaGenerationAgent)
_registry.register("writing")(WritingAgent)
_registry.register("review")(ReviewAgent)
_registry.register("supervisor")(SupervisorAgent)
