from __future__ import annotations

import time
import uuid
from typing import Any

from app.core.exceptions import ConfigurationError
from app.security.hashing import HashingService


class JWTHandler:
    def __init__(
        self,
        secret: str | None = None,
        algorithm: str = "HS256",
        access_token_ttl: int = 3600,
        refresh_token_ttl: int = 2592000,
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._access_token_ttl = access_token_ttl
        self._refresh_token_ttl = refresh_token_ttl
        self._hashing = HashingService()

    async def create_access_token(
        self, subject: str, claims: dict[str, Any] | None = None
    ) -> str:
        import jwt as pyjwt
        if not self._secret:
            raise ConfigurationError("JWT secret not configured", key="jwt_secret")
        now = time.time()
        payload: dict[str, Any] = {
            "sub": subject,
            "exp": now + self._access_token_ttl,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "type": "access",
            **(claims or {}),
        }
        return pyjwt.encode(payload, self._secret, algorithm=self._algorithm)

    async def create_refresh_token(self, subject: str) -> str:
        import jwt as pyjwt
        if not self._secret:
            raise ConfigurationError("JWT secret not configured", key="jwt_secret")
        now = time.time()
        payload: dict[str, Any] = {
            "sub": subject,
            "exp": now + self._refresh_token_ttl,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "type": "refresh",
        }
        return pyjwt.encode(payload, self._secret, algorithm=self._algorithm)

    async def verify_token(self, token: str) -> dict[str, Any]:
        import jwt as pyjwt
        if not self._secret:
            raise ConfigurationError("JWT secret not configured", key="jwt_secret")
        try:
            return pyjwt.decode(
                token, self._secret, algorithms=[self._algorithm]
            )
        except pyjwt.ExpiredSignatureError:
            raise ConfigurationError("Token has expired", key="token") from None
        except pyjwt.InvalidTokenError as exc:
            raise ConfigurationError(f"Invalid token: {exc}", key="token") from None

    async def refresh_access_token(self, refresh_token: str) -> str:
        payload = await self.verify_token(refresh_token)
        if payload.get("type") != "refresh":
            raise ConfigurationError("Invalid refresh token", key="token")
        return await self.create_access_token(subject=payload["sub"])

    async def hash_password(self, password: str) -> str:
        return await self._hashing.hash_password(password)

    async def verify_password(self, password: str, hashed: str) -> bool:
        return await self._hashing.verify_password(password, hashed)
