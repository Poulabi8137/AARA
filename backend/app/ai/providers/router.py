from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.ai.providers.base import (
    BaseLLMProvider,
    LLMCapabilities,
    LLMConfig,
    LLMMessage,
    LLMResponse,
)


@dataclass
class SelectionCriteria:
    preferred_provider: str | None = None
    preferred_models: list[str] = field(default_factory=list)
    min_context_tokens: int = 0
    max_cost_per_1k: float = float("inf")
    max_latency_ms: float = float("inf")
    required_features: list[str] = field(default_factory=list)
    requires_streaming: bool = False
    requires_functions: bool = False
    requires_vision: bool = False
    requires_json_mode: bool = False
    estimated_input_tokens: int = 0
    failover_enabled: bool = True


@dataclass
class ProviderScore:
    provider_id: str
    model: str
    score: float = 0.0
    cost_score: float = 0.0
    latency_score: float = 0.0
    capability_score: float = 0.0
    health_score: float = 0.0
    reason: str = ""


@dataclass
class RoutingResult:
    provider_id: str
    model: str
    score: float
    alternatives: list[tuple[str, str, float]] = field(default_factory=list)


class ProviderRouter:
    def __init__(self) -> None:
        self._providers: dict[str, BaseLLMProvider] = {}
        self._capabilities: dict[str, dict[str, LLMCapabilities]] = {}
        self._latency_history: dict[str, list[float]] = {}
        self._health_status: dict[str, bool] = {}
        self._default_model_map: dict[str, str] = {
            "openai": "gpt-4o-mini",
            "gemini": "gemini-1.5-flash",
            "groq": "llama-3.1-8b-instant",
            "openrouter": "gpt-4o-mini",
            "ollama": "llama3.2",
        }

    def register_provider(
        self, provider: BaseLLMProvider, capabilities: dict[str, LLMCapabilities] | None = None
    ) -> None:
        self._providers[provider.provider_id] = provider
        if capabilities:
            self._capabilities[provider.provider_id] = capabilities
        self._health_status[provider.provider_id] = True

    def _score_provider(
        self, pid: str, model: str, criteria: SelectionCriteria
    ) -> ProviderScore:
        score = ProviderScore(provider_id=pid, model=model)
        caps = self._capabilities.get(pid, {}).get(model)

        if not caps:
            return score

        capability_score = 0.0
        reasons = []

        if criteria.min_context_tokens > 0:
            if caps.max_context_tokens >= criteria.min_context_tokens:
                capability_score += 25
                reasons.append("sufficient_context")
            else:
                capability_score -= 50
                reasons.append("insufficient_context")

        if criteria.requires_streaming and not caps.supports_streaming:
            capability_score -= 30
            reasons.append("no_streaming")

        if criteria.requires_functions and not caps.supports_functions:
            capability_score -= 20
            reasons.append("no_functions")

        if criteria.requires_vision and not caps.supports_vision:
            capability_score -= 20
            reasons.append("no_vision")

        if criteria.requires_json_mode and not caps.supports_json_mode:
            capability_score -= 15
            reasons.append("no_json_mode")

        for feat in criteria.required_features:
            if (
                feat == "streaming" and caps.supports_streaming
                or feat == "functions" and caps.supports_functions
                or feat == "vision" and caps.supports_vision
            ):
                capability_score += 10

        cost_score = 0.0
        if caps.cost_per_1k_input > 0:
            estimated_cost = caps.cost_per_1k_input * (criteria.estimated_input_tokens / 1000)
            if estimated_cost <= criteria.max_cost_per_1k:
                cost_score = 30 * (1 - estimated_cost / max(criteria.max_cost_per_1k, 0.001))
            else:
                cost_score = -10

        latency_score = 0.0
        history = self._latency_history.get(pid, [])
        if history:
            avg_latency = sum(history) / len(history)
            if avg_latency <= criteria.max_latency_ms:
                latency_score = 20 * (1 - avg_latency / max(criteria.max_latency_ms, 0.001))
            else:
                latency_score = -10

        health_score = 20.0 if self._health_status.get(pid, False) else -100.0

        total = capability_score + cost_score + latency_score + health_score
        score.capability_score = capability_score
        score.cost_score = cost_score
        score.latency_score = latency_score
        score.health_score = health_score
        score.score = total
        score.reason = "; ".join(reasons)
        return score

    def select(self, criteria: SelectionCriteria) -> RoutingResult | None:
        candidates: list[ProviderScore] = []

        for pid, provider in self._providers.items():
            model = next(
                (m for m in criteria.preferred_models if m in self._capabilities.get(pid, {})),
                self._default_model_map.get(pid) or provider.model,
            )

            ps = self._score_provider(pid, model, criteria)
            candidates.append(ps)

        if not candidates:
            return None

        candidates.sort(key=lambda s: s.score, reverse=True)
        best = candidates[0]

        if criteria.failover_enabled and best.score < 0:
            healthy = [c for c in candidates if self._health_status.get(c.provider_id, False)]
            if healthy:
                best = healthy[0]

        alternatives = [
            (c.provider_id, c.model, c.score)
            for c in candidates[1:4]
        ]

        return RoutingResult(
            provider_id=best.provider_id,
            model=best.model,
            score=best.score,
            alternatives=alternatives,
        )

    async def chat_with_failover(
        self, messages: list[LLMMessage], criteria: SelectionCriteria
    ) -> LLMResponse:
        result = self.select(criteria)
        if not result:
            msg = "No available provider matches the criteria"
            raise RuntimeError(msg)

        provider = self._providers[result.provider_id]
        config = LLMConfig(model=result.model)
        provider.config = config

        last_error: Exception | None = None
        tried: list[str] = [result.provider_id]

        for _ in range(3):
            try:
                start = time.time()
                response = await provider.chat(messages)
                latency = (time.time() - start) * 1000
                self._record_latency(result.provider_id, latency)
                return response
            except Exception as e:
                last_error = e
                self._health_status[result.provider_id] = False
                if criteria.failover_enabled and result.alternatives:
                    alt = result.alternatives.pop(0)
                    if alt[0] not in tried:
                        tried.append(alt[0])
                        provider = self._providers[alt[0]]
                        provider.config = LLMConfig(model=alt[1])
                        continue
                break

        raise RuntimeError(f"All providers failed: {last_error}") from last_error

    def _record_latency(self, provider_id: str, latency_ms: float) -> None:
        if provider_id not in self._latency_history:
            self._latency_history[provider_id] = []
        self._latency_history[provider_id].append(latency_ms)
        if len(self._latency_history[provider_id]) > 100:
            self._latency_history[provider_id] = self._latency_history[provider_id][-100:]

    def list_available(self) -> list[str]:
        return list(self._providers.keys())

    def get_provider(self, provider_id: str) -> BaseLLMProvider | None:
        return self._providers.get(provider_id)

    def clear(self) -> None:
        self._providers.clear()
        self._capabilities.clear()
        self._latency_history.clear()
        self._health_status.clear()
