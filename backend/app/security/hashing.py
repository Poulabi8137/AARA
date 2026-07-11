from __future__ import annotations

import hashlib
import hmac
from typing import Any


def _get_bcrypt():
    try:
        from passlib.hash import bcrypt
        bcrypt.hash("test")
        return bcrypt
    except Exception:
        try:
            import bcrypt as _bcrypt_module
            return _bcrypt_module
        except ImportError:
            return None


_BCRYPT = _get_bcrypt()


class HashingService:
    def __init__(self, secret: str | None = None) -> None:
        self._secret = secret

    async def hash_password(self, password: str) -> str:
        if _BCRYPT is not None:
            if hasattr(_BCRYPT, "hash"):
                return _BCRYPT.hash(password)
            return _BCRYPT.hashpw(password.encode(), _BCRYPT.gensalt()).decode()
        return self._pbkdf2_hash(password)

    async def verify_password(self, password: str, hashed: str) -> bool:
        if _BCRYPT is not None and hashed.startswith("$2b$"):
            if hasattr(_BCRYPT, "verify"):
                return _BCRYPT.verify(password, hashed)
            return _BCRYPT.checkpw(password.encode(), hashed.encode())
        if not hashed.startswith("$2b$"):
            return self._pbkdf2_hash(password) == hashed
        return False

    async def hash(self, data: str, algorithm: str = "sha256") -> str:
        h = hashlib.new(algorithm)
        h.update(data.encode())
        return h.hexdigest()

    async def hmac_hash(self, data: str, key: str | None = None) -> str:
        secret = (key or self._secret or "").encode()
        return hmac.new(secret, data.encode(), hashlib.sha256).hexdigest()

    async def verify_hmac(self, data: str, signature: str, key: str | None = None) -> bool:
        expected = await self.hmac_hash(data, key)
        return hmac.compare_digest(expected, signature)

    async def hash_dict(self, data: dict[str, Any]) -> str:
        import json
        serialized = json.dumps(data, sort_keys=True)
        return await self.hash(serialized)

    def _pbkdf2_hash(self, data: str) -> str:
        salt = hashlib.sha256((data + (self._secret or "")).encode()).hexdigest()[:16]
        return hashlib.pbkdf2_hmac("sha256", data.encode(), salt.encode(), 600000).hex()
