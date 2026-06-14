from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.api.router import (
    auth_router,
    projects_router,
    sessions_router,
    reports_router,
    health_router,
    documents_router,
    agents_router,
    retrieval_debug_router,
    summarizer_debug_router,
    gap_debug_router,
    report_generator_router,
    evaluation_router,
    human_approval_router,
)
from app.core.logging import setup_logging, get_logger
from app.middleware.setup import setup_middleware
from app.middleware.error_handler import setup_exception_handlers
from app.core.observability import setup_observability
from app.agents.registry import AgentRegistry
from app.llm.factory import validate_provider_config
import os

from app.core.config import get_settings
from app.redis.client import get_redis, close_redis

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("starting AgentWatch API")

    settings = get_settings()

    # ── Secret validation (fail-fast) ──────────────────────────
    secret_key = settings.secret_key or os.environ.get("SECRET_KEY", "")
    if not secret_key or secret_key in ("", "change-me-in-production"):
        msg = (
            "FATAL: SECRET_KEY is not set or is using a default value. "
            "Set SECRET_KEY environment variable to a secure random string (min 32 chars)."
        )
        logger.error(msg)
        raise RuntimeError(msg)
    if len(secret_key) < 32:
        msg = (
            f"FATAL: SECRET_KEY is too short ({len(secret_key)} chars). "
            "Must be at least 32 characters."
        )
        logger.error(msg)
        raise RuntimeError(msg)

    # Init Redis if configured and attach to app.state for lazy access by middleware
    if settings.redis_url and settings.redis_url != "memory":
        try:
            app.state.redis_client = await get_redis()
            logger.info("Redis connection established")
        except Exception as exc:
            logger.warning(
                "Redis unavailable, rate limiting disabled",
                extra={"error": str(exc)},
            )
            app.state.redis_client = None
    else:
        app.state.redis_client = None
        logger.info("Redis not configured, rate limiting disabled")

    AgentRegistry.discover()
    registered = AgentRegistry.list_agents()
    logger.info("agent registry seeded", extra={"agent_count": len(registered), "agents": [a["name"] for a in registered]})

    # LLM provider startup validation
    provider_errors = validate_provider_config(settings)
    if provider_errors:
        for err in provider_errors:
            logger.error("llm provider configuration error", extra={"error": err})
        logger.warning(
            "LLM provider has configuration issues — falling back to MockProvider",
            extra={"errors": provider_errors},
        )
    else:
        logger.info(
            "llm provider validated",
            extra={"provider": settings.llm_provider, "model": settings.llm_model},
        )

    yield

    logger.info("shutting down AgentWatch API")
    if app.state.redis_client is not None:
        await close_redis()
        logger.info("Redis connection closed")


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title="AgentWatch API",
        description="AI-powered autonomous agent observability and governance platform",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.state.redis_client = None

    setup_middleware(app)
    setup_exception_handlers(app)
    setup_observability(app)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(projects_router)
    app.include_router(sessions_router)
    app.include_router(reports_router)
    app.include_router(documents_router)
    app.include_router(agents_router)
    app.include_router(retrieval_debug_router)
    app.include_router(summarizer_debug_router)
    app.include_router(gap_debug_router)
    app.include_router(report_generator_router)
    app.include_router(evaluation_router)
    app.include_router(human_approval_router)

    return app


app = create_app()
