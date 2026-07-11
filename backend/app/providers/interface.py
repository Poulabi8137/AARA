from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProviderStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ProviderConfig:
    provider_id: str
    model: str = ""
    api_key: str | None = None
    base_url: str | None = None
    timeout: float = 30.0
    max_retries: int = 3
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderCapability:
    name: str
    version: str
    models: list[str]
    features: list[str]
    max_context_tokens: int = 0
    max_output_tokens: int = 0
    supports_streaming: bool = False
    supports_functions: bool = False


@dataclass
class ProviderHealth:
    status: ProviderStatus = ProviderStatus.UNKNOWN
    latency_ms: float = 0.0
    error: str | None = None
    last_check: float = 0.0


class BaseProvider(ABC):
    provider_id: str = ""
    model: str = ""
    max_context_tokens: int = 0

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @abstractmethod
    async def initialize(self) -> None: ...

    @abstractmethod
    async def health_check(self) -> ProviderHealth: ...

    @abstractmethod
    async def get_capabilities(self) -> ProviderCapability: ...

    @abstractmethod
    async def close(self) -> None: ...
