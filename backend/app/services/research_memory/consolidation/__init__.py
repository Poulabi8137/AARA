from app.services.research_memory.consolidation.aging import MemoryAgingEngine
from app.services.research_memory.consolidation.base import (
    ConsolidationConfig,
    ConsolidationResult,
    ConsolidationStrategy,
)
from app.services.research_memory.consolidation.engine import ConsolidationEngine
from app.services.research_memory.consolidation.evolution import KnowledgeEvolution
from app.services.research_memory.consolidation.paper_strategy import (
    PaperConsolidationStrategy,
)
from app.services.research_memory.consolidation.project_strategy import (
    ProjectConsolidationStrategy,
)
from app.services.research_memory.consolidation.session_strategy import (
    SessionConsolidationStrategy,
)

__all__ = [
    "ConsolidationConfig",
    "ConsolidationEngine",
    "ConsolidationResult",
    "ConsolidationStrategy",
    "KnowledgeEvolution",
    "MemoryAgingEngine",
    "PaperConsolidationStrategy",
    "ProjectConsolidationStrategy",
    "SessionConsolidationStrategy",
]
