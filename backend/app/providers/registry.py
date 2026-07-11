from __future__ import annotations

from typing import Any

from app.core.exceptions import RegistryError
from app.providers.interface import BaseProvider, ProviderConfig


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, type[BaseProvider]] = {}
        self._instances: dict[str, BaseProvider] = {}

    def register(self, provider_id: str | None = None) -> Any:
        def decorator(cls: type[BaseProvider]) -> type[BaseProvider]:
            pid = provider_id or getattr(cls, "provider_id", None)
            if not pid:
                msg = f"Provider class {cls.__name__} must define provider_id"
                raise RegistryError(msg)
            if pid in self._providers:
                raise RegistryError(f"Provider '{pid}' already registered")
            self._providers[pid] = cls
            return cls
        return decorator

    def get_provider(self, provider_id: str, config: ProviderConfig | None = None) -> BaseProvider:
        if provider_id in self._instances:
            return self._instances[provider_id]
        cls = self._providers.get(provider_id)
        if not cls:
            raise RegistryError(f"Provider '{provider_id}' not found")
        instance = cls(config or ProviderConfig(provider_id=provider_id))
        self._instances[provider_id] = instance
        return instance

    def get_available(self) -> list[str]:
        return list(self._providers.keys())

    def list_providers(self) -> list[dict[str, str]]:
        return [
            {"id": pid, "class": cls.__name__}
            for pid, cls in self._providers.items()
        ]

    def clear_instances(self) -> None:
        self._instances.clear()

    def unregister(self, provider_id: str) -> None:
        self._providers.pop(provider_id, None)
        self._instances.pop(provider_id, None)
