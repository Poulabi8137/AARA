from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.observability.logging import get_logger

naming_convention: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=naming_convention)


class Base(DeclarativeBase):
    metadata = metadata


class DatabaseManager:
    def __init__(self, database_url: str, pool_size: int = 10, max_overflow: int = 20) -> None:
        kwargs: dict[str, object] = {"echo": False}
        if "sqlite" not in database_url:
            kwargs["pool_size"] = pool_size
            kwargs["max_overflow"] = max_overflow
            kwargs["poolclass"] = AsyncAdaptedQueuePool
        self._engine = create_async_engine(database_url, **kwargs)
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self._pool_size = pool_size
        self._max_overflow = max_overflow

    @property
    def engine(self) -> Any:
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory

    def create_session(self) -> AsyncSession:
        return self._session_factory()

    async def get_session(self) -> AsyncSession:
        return self._session_factory()

    async def init_db(self) -> None:
        logger = get_logger("aara.database")
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("database_tables_created")

    async def close_db(self) -> None:
        logger = get_logger("aara.database")
        await self._engine.dispose()
        logger.info("database_engine_disposed")

    def get_pool_status(self) -> dict[str, Any]:
        """Get connection pool status for monitoring."""
        if "sqlite" in str(self._engine.url):
            return {"type": "sqlite", "pooled": False}
        pool = self._engine.pool
        return {
            "type": "async",
            "pooled": True,
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "max_size": self._pool_size + self._max_overflow,
        }


_db_manager: DatabaseManager | None = None


def init_db_manager(
    database_url: str, pool_size: int = 10, max_overflow: int = 20
) -> DatabaseManager:
    global _db_manager
    _db_manager = DatabaseManager(
        database_url=database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
    )
    return _db_manager


def get_db_manager() -> DatabaseManager:
    if _db_manager is None:
        raise RuntimeError("DatabaseManager not initialized")
    return _db_manager


async def get_db() -> AsyncGenerator[AsyncSession, Any]:
    manager = get_db_manager()
    session = manager.create_session()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
