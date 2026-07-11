from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.exceptions import DependencyError


class ServiceContainer:
    def __init__(self) -> None:
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Callable[[], Any]] = {}

    def register_singleton(self, key: str, instance: Any) -> None:
        self._services[key] = instance

    def register_factory(self, key: str, factory: Callable[[], Any]) -> None:
        self._factories[key] = factory

    def resolve(self, key: str) -> Any:
        if key in self._services:
            return self._services[key]

        factory = self._factories.get(key)
        if factory is not None:
            instance = factory()
            self._services[key] = instance
            return instance

        raise DependencyError(key)

    def has(self, key: str) -> bool:
        return key in self._services or key in self._factories

    def clear(self) -> None:
        self._services.clear()

    def registered_keys(self) -> list[str]:
        return list(self._services.keys()) + list(self._factories.keys())
