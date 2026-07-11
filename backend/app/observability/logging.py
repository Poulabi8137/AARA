from __future__ import annotations

import logging
import sys
import uuid
from typing import Any

import structlog
from structlog.typing import EventDict


def configure_logging(log_level: str = "INFO", environment: str = "development") -> None:
    """Configure structured logging with correlation ID support."""
    timestamps = environment == "production"

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True) if timestamps else structlog.dev.set_exc_info,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        inject_correlation_id,
        add_service_context,
    ]

    if environment == "production":
        processors.append(structlog.processors.JSONRenderer(sort_keys=True))
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True, sort_keys=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level.upper())
    root_logger.addHandler(handler)

    structlog.stdlib.recreate_defaults(log_level=log_level.upper())


def get_logger(name: str | None = None) -> Any:
    return structlog.get_logger(name)


def inject_correlation_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Inject correlation ID from contextvars into log event."""
    correlation_id = structlog.contextvars.get_contextvars().get("correlation_id")
    if not correlation_id:
        correlation_id = f"req-{uuid.uuid4().hex[:8]}"
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

    event_dict["correlation_id"] = correlation_id
    return event_dict


def add_service_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add service context to log events."""
    event_dict["service"] = "aara-backend"
    event_dict["version"] = "0.3.0"
    return event_dict


def setup_logging(log_level: str = "INFO", environment: str = "development") -> Any:
    configure_logging(log_level, environment)
    return get_logger
