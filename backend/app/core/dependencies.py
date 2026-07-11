from __future__ import annotations

from fastapi import Request

from app.core.config import GlobalConfig
from app.core.config_loader import ApplicationContext


def get_app_context(request: Request) -> ApplicationContext:
    context: ApplicationContext = request.app.state.context
    return context


def get_config(request: Request) -> GlobalConfig:
    context: ApplicationContext = request.app.state.context
    return context.config
