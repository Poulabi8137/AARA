from __future__ import annotations

from typing import Any

from app.providers.interface import BaseProvider, ProviderConfig
from app.providers.registry import ProviderRegistry


class ProviderFactory:
    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry
        self._pre_hooks: list[Any] = []
        self._post_hooks: list[Any] = []

    def register_pre_hook(self, hook: Any) -> None:
        self._pre_hooks.append(hook)

    def register_post_hook(self, hook: Any) -> None:
        self._post_hooks.append(hook)

    def create(self, provider_id: str, config: ProviderConfig | None = None) -> BaseProvider:
        for hook in self._pre_hooks:
            hook(provider_id, config)
        instance = self._registry.get_provider(provider_id, config)
        for hook in self._post_hooks:
            hook(provider_id, instance)
        return instance

    def create_all(self, configs: dict[str, ProviderConfig]) -> dict[str, BaseProvider]:
        return {
            pid: self.create(pid, cfg)
            for pid, cfg in configs.items()
        }
