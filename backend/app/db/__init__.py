"""Database module for AARA backend."""

from app.db.migrations import run_migrations

__all__ = ["run_migrations"]
