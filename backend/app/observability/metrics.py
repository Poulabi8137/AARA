from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MetricPoint:
    name: str
    value: float
    tags: dict[str, str] = field(default_factory=dict)
    timestamp: datetime | None = None


class MetricsCollector:
    def __init__(self) -> None:
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}

    def increment(self, name: str, value: float = 1.0, tags: dict[str, str] | None = None) -> None:
        key = self._tagged_key(name, tags or {})
        self._counters[key] = self._counters.get(key, 0.0) + value

    def gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        key = self._tagged_key(name, tags or {})
        self._gauges[key] = value

    def observe(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        key = self._tagged_key(name, tags or {})
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)

    def get_counter(self, name: str, tags: dict[str, str] | None = None) -> float:
        return self._counters.get(self._tagged_key(name, tags or {}), 0.0)

    def get_gauge(self, name: str, tags: dict[str, str] | None = None) -> float:
        return self._gauges.get(self._tagged_key(name, tags or {}), 0.0)

    def get_histogram(self, name: str, tags: dict[str, str] | None = None) -> list[float]:
        return list(self._histograms.get(self._tagged_key(name, tags or {}), []))

    def get_all_counters(self) -> dict[str, float]:
        return dict(self._counters)

    def get_all_gauges(self) -> dict[str, float]:
        return dict(self._gauges)

    def snapshot(self) -> dict[str, Any]:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {k: len(v) for k, v in self._histograms.items()},
        }

    def reset(self) -> None:
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()

    def _tagged_key(self, name: str, tags: dict[str, str]) -> str:
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"
