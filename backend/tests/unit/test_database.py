from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, get_db_manager, init_db_manager


class TestDatabaseManager:
    @pytest.fixture
    def db_manager(self):
        mgr = init_db_manager("sqlite+aiosqlite://", pool_size=5, max_overflow=10)
        return mgr

    async def test_init_and_close(self, db_manager):
        await db_manager.init_db()
        await db_manager.close_db()

    async def test_create_session(self, db_manager):
        await db_manager.init_db()
        session = db_manager.create_session()
        assert isinstance(session, AsyncSession)
        await session.close()
        await db_manager.close_db()

    async def test_get_db_manager_returns_instance(self, db_manager):
        mgr = get_db_manager()
        assert mgr is db_manager
        await db_manager.close_db()

    def test_base_has_metadata(self):
        assert hasattr(Base, "metadata")

    def test_naming_convention(self):
        from app.core.database import naming_convention
        assert "ix" in naming_convention
        assert "fk" in naming_convention
