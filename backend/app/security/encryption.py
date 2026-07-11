from __future__ import annotations

import base64
from typing import Any

from app.core.exceptions import ConfigurationError


class EncryptionService:
    def __init__(self, key: str | None = None) -> None:
        self._key = key

    def _get_key(self) -> bytes:
        if not self._key:
            raise ConfigurationError("Encryption key not configured", key="encryption_key")
        key_bytes = self._key.encode().ljust(32)[:32]
        return base64.urlsafe_b64encode(key_bytes)

    async def encrypt(self, data: str) -> str:
        from cryptography.fernet import Fernet
        key = self._get_key()
        f = Fernet(key)
        encrypted = f.encrypt(data.encode())
        return encrypted.decode()

    async def decrypt(self, encrypted_data: str) -> str:
        from cryptography.fernet import Fernet
        key = self._get_key()
        f = Fernet(key)
        decrypted = f.decrypt(encrypted_data.encode())
        return decrypted.decode()

    async def encrypt_dict(self, data: dict[str, Any]) -> dict[str, str]:
        return {k: await self.encrypt(str(v)) for k, v in data.items()}

    async def decrypt_dict(self, data: dict[str, str]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for k, v in data.items():
            decrypted = await self.decrypt(v)
            result[k] = decrypted
        return result
