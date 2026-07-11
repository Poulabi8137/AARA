from __future__ import annotations

from fastapi import FastAPI, Response

from app.api.routes.ai import router as ai_router
from app.api.routes.auth import router as auth_router
from app.api.routes.citations import router as citations_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.documents import router as documents_router
from app.api.routes.library import router as library_router
from app.api.routes.projects import router as projects_router
from app.api.routes.quality_checks import router as quality_checks_router
from app.api.routes.research import router as research_router
from app.api.routes.search import router as search_router
from app.api.routes.workspaces import router as workspaces_router
from app.core.events import lifespan
from app.core.middleware import register_middleware
from app.observability.health import HealthChecker
from app.observability.prometheus_metrics import get_prometheus_metrics

health_checker = HealthChecker(version="0.1.0")


def register_routes(app: FastAPI) -> None:
    app.include_router(auth_router)
    app.include_router(ai_router)
    app.include_router(workspaces_router)
    app.include_router(projects_router)
    app.include_router(research_router)
    app.include_router(citations_router)
    app.include_router(library_router)
    app.include_router(documents_router)
    app.include_router(dashboard_router)
    app.include_router(search_router)
    app.include_router(quality_checks_router)


def create_app() -> FastAPI:
    from app.core.config import GlobalConfig
    config = GlobalConfig()

    app = FastAPI(
        title="AARA API",
        version="0.1.0",
        description="Autonomous AI Research Assistant",
        lifespan=lifespan,
    )

    app.state.cors_origins = config.cors_origins
    app.state.config = config

    register_middleware(app)
    register_routes(app)

    @app.get("/health")
    async def health() -> dict:
        report = await health_checker.check()
        return {
            "status": report.overall_status,
            "version": report.version,
            "uptime_seconds": report.uptime,
            "services": [
                {
                    "name": s.name,
                    "status": s.status,
                    "message": s.message,
                    "details": s.details,
                }
                for s in report.services
            ],
        }

    @app.get("/health/live")
    async def liveness() -> dict:
        report = health_checker.check_liveness()
        return {
            "status": report.overall_status,
            "version": report.version,
            "uptime_seconds": report.uptime,
        }

    @app.get("/health/ready")
    async def readiness() -> dict:
        report = await health_checker.check_readiness()
        return {
            "status": report.overall_status,
            "version": report.version,
            "uptime_seconds": report.uptime,
            "services": [
                {
                    "name": s.name,
                    "status": s.status,
                    "message": s.message,
                }
                for s in report.services
            ],
        }

    @app.get("/metrics")
    async def metrics() -> Response:
        output = get_prometheus_metrics()
        return Response(
            content=output,
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    return app


app = create_app()
