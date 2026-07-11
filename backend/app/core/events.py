from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config_loader import ApplicationContext, ApplicationInitializer
from app.observability.logging import get_logger
from app.observability.prometheus_metrics import BACKGROUND_TASKS_COMPLETED

logger = get_logger("aara.events")


async def startup_event(app: FastAPI) -> None:
    start_time = time.monotonic()
    initializer = ApplicationInitializer(env_file=".env")
    context = await initializer.initialize()
    app.state.context = context
    app.state.startup_time = start_time

    startup_duration = time.monotonic() - start_time
    logger.info("server_startup", startup_duration_seconds=round(startup_duration, 3))

    BACKGROUND_TASKS_COMPLETED.labels(status="startup_complete").inc()


async def shutdown_event(app: FastAPI) -> None:
    context: ApplicationContext | None = getattr(app.state, "context", None)
    if context is not None:
        initializer = ApplicationInitializer()
        await initializer.shutdown(context)
    logger.info("server_shutdown")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await startup_event(app)
    yield
    await shutdown_event(app)


def register_events(app: FastAPI) -> None:
    pass
