from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.exceptions import ConfigurationError


@dataclass
class TokenPayload:
    sub: str
    exp: float
    iat: float
    jti: str = ""
    claims: dict[str, Any] = field(default_factory=dict)


class TokenService:
    def __init__(self, secret: str | None = None, algorithm: str = "HS256") -> None:
        self._secret = secret
        self._algorithm = algorithm

    async def create_token(
        self,
        subject: str,
        expires_in: float = 3600.0,
        claims: dict[str, Any] | None = None,
    ) -> str:
        import jwt as pyjwt
        if not self._secret:
            raise ConfigurationError("Token secret not configured", key="token_secret")
        now = time.time()
        payload: dict[str, Any] = {
            "sub": subject,
            "exp": now + expires_in,
            "iat": now,
            "jti": str(uuid.uuid4()),
            **(claims or {}),
        }
        return pyjwt.encode(payload, self._secret, algorithm=self._algorithm)

    async def verify_token(self, token: str) -> TokenPayload:
        import jwt as pyjwt
        if not self._secret:
            raise ConfigurationError("Token secret not configured", key="token_secret")
        try:
            decoded = pyjwt.decode(token, self._secret, algorithms=[self._algorithm])
            return TokenPayload(
                sub=decoded.get("sub", ""),
                exp=decoded.get("exp", 0.0),
                iat=decoded.get("iat", 0.0),
                jti=decoded.get("jti", ""),
                claims={k: v for k, v in decoded.items() if k not in ("sub", "exp", "iat", "jti")},
            )
        except pyjwt.ExpiredSignatureError:
            raise ConfigurationError("Token has expired", key="token") from None
        except pyjwt.InvalidTokenError as exc:
            raise ConfigurationError(f"Invalid token: {exc}", key="token") from None

    async def create_api_key(self, prefix: str = "aara_") -> str:
        import secrets
        return f"{prefix}{secrets.token_urlsafe(32)}"
