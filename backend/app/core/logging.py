from __future__ import annotations

import logging
import sys
import json
from datetime import datetime, timezone

from app.core.config import get_settings

settings = get_settings()


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra"):
            log["extra"] = record.extra
        return json.dumps(log)


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    root.handlers.clear()
    root.addHandler(handler)

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
