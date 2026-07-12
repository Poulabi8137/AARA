from __future__ import annotations

from app.core.logging import get_logger
from alembic.config import Config
from alembic import command
import os

logger = get_logger("db.migrations")


def get_alembic_config():
    """Get Alembic configuration."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    config = Config(os.path.join(base_dir, "alembic.ini"))
    return config


async def run_migrations():
    """Run database migrations."""
    try:
        config = get_alembic_config()
        command.upgrade(config, "head")
        logger.info("database migrations completed successfully")
    except Exception as exc:
        logger.error("database migration failed", extra={"error": str(exc)})
        raise