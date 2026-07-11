from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def app_client(tmp_path, monkeypatch) -> AsyncIterator[AsyncClient]:
    """A real FastAPI app wired to a throwaway SQLite DB, exercised over real
    HTTP (via ASGI transport) so middleware, DI, and routing all run for real
    instead of being mocked out as in the unit-test suite."""
    db_path = tmp_path / f"integration_{uuid.uuid4().hex}.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("DATABASE_URL_SYNC", f"sqlite:///{db_path}")
    monkeypatch.setenv("JWT_SECRET", "integration-test-jwt-secret-key-32-chars-min")
    monkeypatch.setenv("ENCRYPTION_KEY", "integration-test-encryption-key")
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")

    from app.main import create_app

    app = create_app()

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
