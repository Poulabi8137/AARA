from __future__ import annotations

import os
from abc import ABC, abstractmethod


class SecretsBackend(ABC):
    @abstractmethod
    async def get(self, key: str) -> str | None: ...


class EnvironmentSecretsBackend(SecretsBackend):
    PREFIX = "AARA_SECRET_"

    async def get(self, key: str) -> str | None:
        return os.environ.get(f"{self.PREFIX}{key}")


class SecretsResolver:
    def __init__(self) -> None:
        self._backends: list[SecretsBackend] = [
            EnvironmentSecretsBackend(),
        ]

    def add_backend(self, backend: SecretsBackend) -> None:
        self._backends.append(backend)

    async def get(self, key: str) -> str | None:
        for backend in self._backends:
            value = await backend.get(key)
            if value is not None:
                return value
        return None
