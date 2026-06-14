from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

import pytest
from jose import jwt

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    create_refresh_token,
    create_password_reset_token,
    verify_password_reset_token,
    TokenExpiredError,
    TokenInvalidError,
    settings,
)


class TestPasswordHashing:
    def test_hash_and_verify_roundtrip(self):
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed)
        assert not verify_password("WrongPassword", hashed)

    def test_hash_is_different_each_time(self):
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2

    def test_verify_wrong_hash_returns_false(self):
        correct = "TestPassword123!"
        hashed = hash_password(correct)
        assert not verify_password("WrongPassword!", hashed)


class TestAccessToken:
    def test_create_and_decode(self):
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id, {"role": "admin"})
        payload = decode_token(token)
        assert payload["sub"] == user_id
        assert payload["type"] == "access"
        assert payload["role"] == "admin"
        assert payload["token_version"] == settings.token_version

    def test_decode_includes_issued_at(self):
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id)
        payload = decode_token(token)
        assert "iat" in payload
        assert "exp" in payload

    def test_expired_token_raises_token_expired_error(self):
        payload = {
            "sub": "test-user",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "type": "access",
            "token_version": settings.token_version,
        }
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
        with pytest.raises(TokenExpiredError):
            decode_token(token)

    def test_invalid_token_raises_token_invalid_error(self):
        with pytest.raises(TokenInvalidError):
            decode_token("invalid.token.here")

    def test_malformed_token_raises_token_invalid_error(self):
        with pytest.raises(TokenInvalidError):
            decode_token("not-a-jwt")

    def test_tampered_token_raises_token_invalid_error(self):
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id)
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + ".invalidsignature"
        with pytest.raises(TokenInvalidError):
            decode_token(tampered)


class TestRefreshToken:
    def test_create_has_refresh_type(self):
        user_id = str(uuid.uuid4())
        token = create_refresh_token(user_id)
        payload = decode_token(token)
        assert payload["type"] == "refresh"
        assert payload["sub"] == user_id
        assert payload["token_version"] == settings.token_version

    def test_refresh_cannot_be_used_as_access(self):
        user_id = str(uuid.uuid4())
        token = create_refresh_token(user_id)
        payload = decode_token(token)
        assert payload["type"] != "access"


class TestPasswordResetToken:
    def test_create_and_verify(self):
        user_id = str(uuid.uuid4())
        token = create_password_reset_token(user_id)
        result = verify_password_reset_token(token)
        assert result == user_id

    def test_verify_with_access_token_raises(self):
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id)
        with pytest.raises(TokenInvalidError, match="Invalid token type"):
            verify_password_reset_token(token)

    def test_verify_with_refresh_token_raises(self):
        user_id = str(uuid.uuid4())
        token = create_refresh_token(user_id)
        with pytest.raises(TokenInvalidError, match="Invalid token type"):
            verify_password_reset_token(token)

    def test_expired_reset_token_raises(self):
        user_id = str(uuid.uuid4())
        payload = {
            "sub": user_id,
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "type": "password_reset",
        }
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
        with pytest.raises(TokenExpiredError):
            verify_password_reset_token(token)

    def test_invalid_reset_token_raises(self):
        with pytest.raises(TokenInvalidError):
            verify_password_reset_token("invalid.token.here")
