from __future__ import annotations

import time

from app.observability.logging import get_logger
from app.providers.interface import BaseProvider, ProviderHealth, ProviderStatus


class ProviderHealthMonitor:
    def __init__(self, check_interval: float = 60.0) -> None:
        self._health: dict[str, ProviderHealth] = {}
        self._check_interval = check_interval
        self._last_check: dict[str, float] = {}

    async def check(self, provider: BaseProvider) -> ProviderHealth:
        now = time.time()
        last = self._last_check.get(provider.provider_id, 0.0)

        if now - last < self._check_interval and provider.provider_id in self._health:
            return self._health[provider.provider_id]

        try:
            health = await provider.health_check()
        except Exception as exc:
            health = ProviderHealth(
                status=ProviderStatus.UNHEALTHY,
                error=str(exc),
                last_check=now,
            )
            logger = get_logger("aara.providers.health")
            logger.error(
                "provider_health_check_failed",
                provider=provider.provider_id,
                error=str(exc),
            )

        self._health[provider.provider_id] = health
        self._last_check[provider.provider_id] = now
        return health

    async def check_all(self, providers: list[BaseProvider]) -> dict[str, ProviderHealth]:
        results: dict[str, ProviderHealth] = {}
        for provider in providers:
            results[provider.provider_id] = await self.check(provider)
        return results

    def get_status(self, provider_id: str) -> ProviderStatus:
        health = self._health.get(provider_id)
        return health.status if health else ProviderStatus.UNKNOWN

    def is_healthy(self, provider_id: str) -> bool:
        return self.get_status(provider_id) == ProviderStatus.HEALTHY

    def get_all_healthy(self) -> list[str]:
        return [
            pid for pid, health in self._health.items()
            if health.status == ProviderStatus.HEALTHY
        ]

    def clear(self) -> None:
        self._health.clear()
        self._last_check.clear()
