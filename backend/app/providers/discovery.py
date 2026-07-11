from __future__ import annotations

from dataclasses import dataclass, field

from app.providers.interface import ProviderCapability


@dataclass
class ProviderCapabilitySet:
    provider_id: str
    capabilities: list[ProviderCapability] = field(default_factory=list)


class ProviderCapabilityDiscovery:
    def __init__(self) -> None:
        self._capabilities: dict[str, ProviderCapability] = {}

    def register(self, provider_id: str, capability: ProviderCapability) -> None:
        self._capabilities[provider_id] = capability

    def discover(self, provider_id: str) -> ProviderCapability | None:
        return self._capabilities.get(provider_id)

    def discover_all(self) -> list[ProviderCapabilitySet]:
        seen: dict[str, list[ProviderCapability]] = {}
        for pid, cap in self._capabilities.items():
            if pid not in seen:
                seen[pid] = []
            seen[pid].append(cap)
        return [
            ProviderCapabilitySet(provider_id=pid, capabilities=caps)
            for pid, caps in seen.items()
        ]

    def find_by_feature(self, feature: str) -> list[str]:
        return [
            pid for pid, cap in self._capabilities.items()
            if feature in cap.features
        ]

    def find_by_model(self, model: str) -> list[str]:
        return [
            pid for pid, cap in self._capabilities.items()
            if model in cap.models
        ]

    def clear(self) -> None:
        self._capabilities.clear()
