from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()


class TokenError(Exception):
    pass


class TokenExpiredError(TokenError):
    pass


class TokenInvalidError(TokenError):
    pass


def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        password = password[:72]
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "type": "access",
        "token_version": settings.token_version,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
        "type": "refresh",
        "token_version": settings.token_version,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"verify_exp": True},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except JWTError:
        raise TokenInvalidError("Invalid or malformed token")


def create_password_reset_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(hours=settings.reset_token_expire_hours),
        "type": "password_reset",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def verify_password_reset_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        if payload.get("type") != "password_reset":
            raise TokenInvalidError("Invalid token type")
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Reset token has expired")
    except JWTError:
        raise TokenInvalidError("Invalid reset token")
