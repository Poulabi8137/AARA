from __future__ import annotations

from app.agents.registration import registry as agent_registry
from app.agents.task_graph import TaskGraph
from app.streaming.manager import EventStreamManager
from app.workflow.engine import WorkflowEngine

_event_manager: EventStreamManager | None = None
_workflow_engine: WorkflowEngine | None = None


def get_event_manager() -> EventStreamManager:
    global _event_manager
    if _event_manager is None:
        _event_manager = EventStreamManager()
    return _event_manager


def get_workflow_engine() -> WorkflowEngine:
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine(task_graph=TaskGraph())
    return _workflow_engine


def _build_qdrant_retriever():
    """Return a QdrantRetriever if an embedder is available, else None."""
    try:
        from app.ai.retrieval.qdrant_retriever import QdrantRetriever
        from app.core.config import GlobalConfig

        config = GlobalConfig()
        qdrant_url = config.qdrant_url

        if not config.openai_api_key:
            return None

        from app.ai.embedding.openai_embedder import OpenAIEmbedder
        embedder = OpenAIEmbedder(api_key=config.openai_api_key)

        return QdrantRetriever(
            embedder=embedder,
            qdrant_url=qdrant_url,
            qdrant_api_key=config.qdrant_api_key,
        )
    except Exception:
        return None


def get_research_service():
    from app.agents.supervisor import SupervisorAgent
    from app.ai.evaluation.engine import EvaluationEngine
    from app.repositories.project_repository import ProjectRepository
    from app.repositories.session_repository import SessionRepository
    from app.services.research_service import ResearchService
    from app.streaming.dispatcher_adapter import StreamEventDispatcher

    retriever = _build_qdrant_retriever()
    stream_dispatcher = StreamEventDispatcher(get_event_manager())
    supervisor = SupervisorAgent(
        agent_registry=agent_registry,
        event_dispatcher=stream_dispatcher,
        evaluation_engine=EvaluationEngine(),
    )

    # Inject retriever/event_dispatcher into the cached ResearchAgent instance
    if "research" in agent_registry:
        research_agent = agent_registry.get("research")
        if retriever is not None and hasattr(research_agent, "_retriever"):
            research_agent._retriever = retriever
        if hasattr(research_agent, "_event_dispatcher"):
            research_agent._event_dispatcher = stream_dispatcher

    return ResearchService(
        session_repo=SessionRepository(),
        project_repo=ProjectRepository(),
        workflow_engine=get_workflow_engine(),
        supervisor=supervisor,
        event_manager=get_event_manager(),
        registry=agent_registry,
    )


def get_dashboard_service():
    from app.repositories.citation_repository import CitationRepository
    from app.repositories.conversation_repository import ConversationRepository
    from app.repositories.paper_repository import PaperRepository
    from app.repositories.project_repository import ProjectRepository
    from app.repositories.session_repository import SessionRepository
    from app.repositories.workspace_repository import WorkspaceRepository
    from app.services.dashboard_service import DashboardService

    return DashboardService(
        event_manager=get_event_manager(),
        session_repo=SessionRepository(),
        project_repo=ProjectRepository(),
        workspace_repo=WorkspaceRepository(),
        paper_repo=PaperRepository(),
        citation_repo=CitationRepository(),
        conversation_repo=ConversationRepository(),
    )
