from __future__ import annotations

import pytest

from app.core.exceptions import ConfigurationError
from app.security.encryption import EncryptionService
from app.security.hashing import HashingService
from app.security.secrets import EnvironmentSecretsBackend, SecretsResolver
from app.security.tokens import TokenService


class TestSecretsResolver:
    @pytest.mark.asyncio
    async def test_resolve_nonexistent(self):
        resolver = SecretsResolver()
        value = await resolver.get("NONEXISTENT_SECRET_KEY_XYZ")
        assert value is None

    def test_environment_backend_prefix(self):
        backend = EnvironmentSecretsBackend()
        assert backend.PREFIX == "AARA_SECRET_"


class TestEncryptionService:
    @pytest.mark.asyncio
    async def test_encrypt_decrypt(self):
        service = EncryptionService(key="test-key-12345678")
        encrypted = await service.encrypt("sensitive data")
        assert encrypted != "sensitive data"
        decrypted = await service.decrypt(encrypted)
        assert decrypted == "sensitive data"

    @pytest.mark.asyncio
    async def test_no_key_raises(self):
        service = EncryptionService()
        with pytest.raises(ConfigurationError):
            await service.encrypt("data")

    @pytest.mark.asyncio
    async def test_encrypt_dict(self):
        service = EncryptionService(key="test-key-12345678")
        encrypted = await service.encrypt_dict({"key": "value"})
        assert "key" in encrypted
        assert encrypted["key"] != "value"

    @pytest.mark.asyncio
    async def test_decrypt_dict(self):
        service = EncryptionService(key="test-key-12345678")
        encrypted = await service.encrypt_dict({"key": "value"})
        decrypted = await service.decrypt_dict(encrypted)
        assert decrypted["key"] == "value"


class TestHashingService:
    @pytest.mark.asyncio
    async def test_hash(self):
        service = HashingService()
        result = await service.hash("hello")
        assert isinstance(result, str)
        assert len(result) == 64

    @pytest.mark.asyncio
    async def test_hmac(self):
        service = HashingService(secret="secret")
        sig = await service.hmac_hash("data")
        assert await service.verify_hmac("data", sig) is True
        assert await service.verify_hmac("data", "wrong") is False

    @pytest.mark.asyncio
    async def test_hash_dict(self):
        service = HashingService()
        result = await service.hash_dict({"a": 1, "b": 2})
        assert isinstance(result, str)
        assert len(result) == 64

    @pytest.mark.asyncio
    async def test_deterministic(self):
        service = HashingService()
        assert await service.hash("hello") == await service.hash("hello")


class TestTokenService:
    @pytest.mark.asyncio
    async def test_create_and_verify(self):
        service = TokenService(secret="my-secret-key")
        token = await service.create_token("user-123", expires_in=3600)
        payload = await service.verify_token(token)
        assert payload.sub == "user-123"
        assert payload.jti != ""

    @pytest.mark.asyncio
    async def test_expired_token(self):
        service = TokenService(secret="my-secret-key")
        token = await service.create_token("user-123", expires_in=-1)
        with pytest.raises(ConfigurationError):
            await service.verify_token(token)

    @pytest.mark.asyncio
    async def test_no_secret_raises(self):
        service = TokenService()
        with pytest.raises(ConfigurationError):
            await service.create_token("user-123")

    @pytest.mark.asyncio
    async def test_create_api_key(self):
        service = TokenService(secret="key")
        api_key = await service.create_api_key()
        assert api_key.startswith("aara_")
        assert len(api_key) > 32
