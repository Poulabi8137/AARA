from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_at: float
    retry_after: float = 0.0


class RateLimiter(ABC):
    @abstractmethod
    async def check(self, key: str, cost: int = 1) -> RateLimitResult: ...

    @abstractmethod
    async def reset(self, key: str) -> None: ...

    @abstractmethod
    async def clear(self) -> None: ...
