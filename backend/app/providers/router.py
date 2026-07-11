from __future__ import annotations

from dataclasses import dataclass, field

from app.providers.interface import BaseProvider, ProviderCapability


@dataclass
class SelectionCriteria:
    preferred_provider: str | None = None
    min_context_tokens: int = 0
    max_cost: float = float("inf")
    max_latency_ms: float = float("inf")
    required_features: list[str] = field(default_factory=list)
    preferred_models: list[str] = field(default_factory=list)


@dataclass
class ProviderScore:
    provider_id: str
    score: float = 0.0
    reason: str = ""


class ProviderRouter:
    def __init__(self) -> None:
        self._providers: dict[str, BaseProvider] = {}
        self._capabilities: dict[str, ProviderCapability] = {}

    def register_provider(self, provider: BaseProvider, capability: ProviderCapability) -> None:
        self._providers[provider.provider_id] = provider
        self._capabilities[provider.provider_id] = capability

    def select(self, criteria: SelectionCriteria) -> tuple[str, BaseProvider] | None:
        if criteria.preferred_provider and criteria.preferred_provider in self._providers:
            return criteria.preferred_provider, self._providers[criteria.preferred_provider]

        scored: list[ProviderScore] = []
        for pid, cap in self._capabilities.items():
            score = 0.0
            reasons = []

            if criteria.min_context_tokens > 0 and cap.max_context_tokens >= criteria.min_context_tokens:  # noqa: E501
                score += 10
                reasons.append("sufficient_context")

            if criteria.required_features:
                matched = sum(1 for f in criteria.required_features if f in cap.features)
                score += matched * 5
                if matched < len(criteria.required_features):
                    continue

            if criteria.preferred_models:
                matched_models = [m for m in criteria.preferred_models if m in cap.models]
                score += len(matched_models) * 3

            scored.append(ProviderScore(pid, score, "; ".join(reasons)))

        if not scored:
            return None

        scored.sort(key=lambda s: s.score, reverse=True)
        best = scored[0]
        return best.provider_id, self._providers[best.provider_id]

    def list_available(self) -> list[str]:
        return list(self._providers.keys())

    def clear(self) -> None:
        self._providers.clear()
        self._capabilities.clear()
