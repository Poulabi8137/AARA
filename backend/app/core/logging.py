from __future__ import annotations

import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings

settings = get_settings()


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter with support for correlation IDs and context."""

    def format(self, record: logging.LogRecord) -> str:
        log: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info and record.exc_info[0]:
            log["exception"] = self.formatException(record.exc_info)

        # Merge structured context from extra fields
        extra = getattr(record, "extra", None) or {}
        if isinstance(extra, dict):
            # Promote key context fields to top level for log aggregation tools
            for key in (
                "request_id",
                "correlation_id",
                "user_id",
                "endpoint",
                "execution_time_ms",
                "status_code",
                "error_type",
                "service",
            ):
                if key in extra:
                    log[key] = extra[key]
            # Remaining extra fields nested under "context"
            remaining = {k: v for k, v in extra.items() if k not in log}
            if remaining:
                log["context"] = remaining

        return json.dumps(log, default=str)


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class LoggerContext:
    """Context manager for adding structured context to all log calls within a scope.

    Usage:
        with LoggerContext(logger, request_id=req_id, user_id=uid):
            logger.info("processing request")
    """

    def __init__(self, logger: logging.Logger, **context: Any) -> None:
        self._logger = logger
        self._context = context

    def __enter__(self) -> logging.Logger:
        return self._logger

    def __exit__(self, *args: Any) -> None:
        pass
