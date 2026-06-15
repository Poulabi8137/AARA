from app.api.auth import router as auth_router
from app.api.projects import router as projects_router
from app.api.sessions import router as sessions_router
from app.api.reports import router as reports_router
from app.api.health import router as health_router
from app.api.documents import router as documents_router
from app.api.agents import router as agents_router
from app.api.retrieval_debug import router as retrieval_debug_router
from app.api.summarizer_debug import router as summarizer_debug_router
from app.api.gap_debug import router as gap_debug_router
from app.api.report_generator import router as report_generator_router
from app.api.evaluation import router as evaluation_router
from app.api.human_approval import router as human_approval_router
from app.api.research_outputs import router as research_outputs_router

__all__ = [
    "auth_router",
    "projects_router",
    "sessions_router",
    "reports_router",
    "health_router",
    "documents_router",
    "agents_router",
    "retrieval_debug_router",
    "summarizer_debug_router",
    "gap_debug_router",
    "report_generator_router",
    "evaluation_router",
    "human_approval_router",
    "research_outputs_router",
]
