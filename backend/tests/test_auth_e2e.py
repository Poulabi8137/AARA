from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient, ASGITransport
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import router as auth_router
from app.db.session import get_db
from app.models.user import User, UserRole
from app.core.security import hash_password, create_access_token, create_refresh_token
from app.core.config import get_settings
from app.services.auth_service import get_current_user

settings = get_settings()


def _make_mock_result(scalar_return=None):
    result = AsyncMock()
    result.scalar_one_or_none = MagicMock(return_value=scalar_return)
    return result


def _make_user(**overrides):
    user = MagicMock()
    user.id = overrides.get("id", uuid.uuid4())
    user.name = overrides.get("name", "Test User")
    user.email = overrides.get("email", "test@example.com")
    user.password_hash = overrides.get("password_hash", hash_password("SecurePass123!"))
    role_val = overrides.get("role", UserRole.RESEARCHER)
    user.role = role_val
    user.created_at = overrides.get("created_at", "2025-01-01T00:00:00+00:00")
    return user


@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def app(mock_session):
    _app = FastAPI()

    async def _get_mock_db():
        yield mock_session

    _app.dependency_overrides[get_db] = _get_mock_db

    _app.include_router(auth_router)

    @_app.get("/me")
    async def me(current_user: User = Depends(get_current_user)):
        return {"id": str(current_user.id), "email": current_user.email}

    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return _app


@pytest.fixture
def client(app):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
class TestRegister:
    async def test_register_success(self, client, mock_session):
        mock_session.execute.return_value = _make_mock_result(None)

        response = await client.post(
            "/auth/register",
            json={
                "name": "New User",
                "email": "new@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()

    async def test_register_duplicate_email_returns_409(self, client, mock_session):
        existing = _make_user(email="dup@example.com")
        mock_session.execute.return_value = _make_mock_result(existing)

        response = await client.post(
            "/auth/register",
            json={
                "name": "Duplicate",
                "email": "dup@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    async def test_register_invalid_email_returns_422(self, client):
        response = await client.post(
            "/auth/register",
            json={
                "name": "Bad Email",
                "email": "not-an-email",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 422

    async def test_register_no_uppercase_password_returns_422(self, client):
        response = await client.post(
            "/auth/register",
            json={
                "name": "No Upper",
                "email": "noupper@example.com",
                "password": "securepass123!",
            },
        )
        assert response.status_code == 422

    async def test_register_no_digit_password_returns_422(self, client):
        response = await client.post(
            "/auth/register",
            json={
                "name": "No Digit",
                "email": "nodigit@example.com",
                "password": "SecurePass!",
            },
        )
        assert response.status_code == 422

    async def test_register_empty_name_returns_422(self, client):
        response = await client.post(
            "/auth/register",
            json={
                "name": "",
                "email": "emptyname@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestLogin:
    async def test_login_success(self, client, mock_session):
        password = "SecurePass123!"
        user = _make_user(password_hash=hash_password(password))
        mock_session.execute.return_value = _make_mock_result(user)

        response = await client.post(
            "/auth/login",
            json={
                "email": user.email,
                "password": password,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password_returns_401(self, client, mock_session):
        user = _make_user(password_hash=hash_password("SecurePass123!"))
        mock_session.execute.return_value = _make_mock_result(user)

        response = await client.post(
            "/auth/login",
            json={
                "email": user.email,
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401

    async def test_login_nonexistent_email_returns_401(self, client, mock_session):
        mock_session.execute.return_value = _make_mock_result(None)

        response = await client.post(
            "/auth/login",
            json={
                "email": "nobody@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestRefresh:
    async def test_refresh_success(self, client, mock_session):
        user = _make_user()
        token = create_refresh_token(str(user.id))
        mock_session.execute.return_value = _make_mock_result(user)

        response = await client.post(
            "/auth/refresh",
            json={
                "refresh_token": token,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_expired_token_returns_401(self, client):
        payload = {
            "sub": str(uuid.uuid4()),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "type": "refresh",
            "token_version": settings.token_version,
        }
        expired = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

        response = await client.post(
            "/auth/refresh",
            json={
                "refresh_token": expired,
            },
        )

        assert response.status_code == 401

    async def test_refresh_invalid_token_returns_401(self, client):
        response = await client.post(
            "/auth/refresh",
            json={
                "refresh_token": "invalid.jwt.here",
            },
        )

        assert response.status_code == 401

    async def test_refresh_access_token_returns_401(self, client):
        user = _make_user()
        access = create_access_token(str(user.id))

        response = await client.post(
            "/auth/refresh",
            json={
                "refresh_token": access,
            },
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestProtectedEndpoints:
    async def test_valid_access_token_allowed(self, client, mock_session):
        user = _make_user()
        token = create_access_token(str(user.id), {"role": user.role.value})
        mock_session.execute.return_value = _make_mock_result(user)

        response = await client.get(
            "/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user.email

    async def test_no_token_returns_401(self, client):
        response = await client.get("/me")
        assert response.status_code == 401

    async def test_expired_access_token_returns_401(self, client):
        payload = {
            "sub": str(uuid.uuid4()),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "type": "access",
            "token_version": settings.token_version,
        }
        expired = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

        response = await client.get(
            "/me",
            headers={"Authorization": f"Bearer {expired}"},
        )

        assert response.status_code == 401

    async def test_refresh_token_as_access_returns_401(self, client):
        user = _make_user()
        refresh = create_refresh_token(str(user.id))

        response = await client.get(
            "/me",
            headers={"Authorization": f"Bearer {refresh}"},
        )

        assert response.status_code == 401

    async def test_malformed_token_returns_401(self, client):
        response = await client.get(
            "/me",
            headers={"Authorization": "Bearer not-a-jwt"},
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestCORS:
    async def test_cors_preflight_allowed_origin(self, client):
        response = await client.options(
            "/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 200
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://localhost:3000"
        )

    async def test_cors_preflight_disallowed_origin(self, client):
        response = await client.options(
            "/auth/login",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        allow_origin = response.headers.get("access-control-allow-origin")
        assert allow_origin is None or allow_origin != "http://evil.com"
