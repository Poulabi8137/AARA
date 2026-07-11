from __future__ import annotations

import pytest

from app.core.di_container import ServiceContainer
from app.core.exceptions import DependencyError


class TestServiceContainer:
    def setup_method(self):
        self.container = ServiceContainer()

    def test_register_and_resolve_singleton(self):
        self.container.register_singleton("db", {"connected": True})
        result = self.container.resolve("db")
        assert result == {"connected": True}

    def test_singleton_returns_same_instance(self):
        self.container.register_singleton("counter", 0)
        obj1 = self.container.resolve("counter")
        obj2 = self.container.resolve("counter")
        assert obj1 is obj2

    def test_factory_is_called_on_resolve(self):
        calls = []
        self.container.register_factory("fresh", lambda: calls.append(1) or {"id": len(calls)})
        result1 = self.container.resolve("fresh")
        result2 = self.container.resolve("fresh")
        assert result1["id"] == 1
        assert result2["id"] == 1
        assert len(calls) == 1

    def test_resolve_unregistered_raises(self):
        with pytest.raises(DependencyError) as exc:
            self.container.resolve("nonexistent")
        assert "nonexistent" in str(exc.value)

    def test_has_registered(self):
        self.container.register_singleton("db", {})
        assert self.container.has("db") is True

    def test_has_unregistered(self):
        assert self.container.has("nothing") is False

    def test_clear(self):
        self.container.register_singleton("db", {})
        self.container.clear()
        assert self.container.has("db") is False

    def test_registered_keys(self):
        self.container.register_singleton("db", {})
        self.container.register_factory("tool", lambda: {})
        keys = self.container.registered_keys()
        assert "db" in keys
        assert "tool" in keys
