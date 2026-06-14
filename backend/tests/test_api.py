from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_register_validation(client: AsyncClient) -> None:
    response = await client.post("/auth/register", json={"name": "", "email": "bad", "password": "short"})
    assert response.status_code == 422
    data = response.json()
    assert "errors" in data


@pytest.mark.asyncio
async def test_login_validation(client: AsyncClient) -> None:
    response = await client.post("/auth/login", json={"email": "not-an-email", "password": "short"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_refresh_no_token(client: AsyncClient) -> None:
    response = await client.post("/auth/refresh", json={"refresh_token": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_projects_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/projects")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sessions_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/sessions")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_reports_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/reports")
    assert response.status_code == 401


# --- Document & Retrieval tests ---

@pytest.mark.asyncio
async def test_documents_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/documents")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_requires_auth(client: AsyncClient) -> None:
    response = await client.post("/documents/upload")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_unsupported_format(client: AsyncClient) -> None:
    result = await client.post("/auth/register", json={
        "name": "Test User", "email": "test@test.com", "password": "password123"
    })
    token = result.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/documents/upload",
        headers=headers,
        files={"file": ("test.exe", b"fake content", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_search_requires_auth(client: AsyncClient) -> None:
    response = await client.post("/retrieval/search", json={
        "query": "test", "top_k": 5
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_context_requires_auth(client: AsyncClient) -> None:
    response = await client.post("/retrieval/context", json={
        "query": "test", "top_k": 5
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_validation(client: AsyncClient) -> None:
    result = await client.post("/auth/register", json={
        "name": "Test User", "email": "test2@test.com", "password": "password123"
    })
    token = result.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post("/retrieval/search", headers=headers, json={
        "query": "", "top_k": 5
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_context_validation(client: AsyncClient) -> None:
    result = await client.post("/auth/register", json={
        "name": "Test User", "email": "test3@test.com", "password": "password123"
    })
    token = result.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post("/retrieval/context", headers=headers, json={
        "query": "", "top_k": 5
    })
    assert response.status_code == 422
