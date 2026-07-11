from __future__ import annotations

import time
from collections import deque

from app.rate_limiting.interface import RateLimiter, RateLimitResult


class SlidingWindowLimiter(RateLimiter):
    def __init__(self, default_max_requests: int = 100, default_window_ms: float = 1000.0) -> None:
        self._windows: dict[str, deque[float]] = {}
        self._config: dict[str, tuple[int, float]] = {}
        self._default_max_requests = default_max_requests
        self._default_window_ms = default_window_ms

    def configure(self, key: str, max_requests: int, window_ms: float) -> None:
        self._config[key] = (max_requests, window_ms)
        if key not in self._windows:
            self._windows[key] = deque()

    async def check(self, key: str, cost: int = 1) -> RateLimitResult:
        now = time.time()
        if key not in self._windows:
            self._windows[key] = deque()

        max_requests, window_ms = self._config.get(
            key, (self._default_max_requests, self._default_window_ms)
        )
        window_seconds = window_ms / 1000.0
        cutoff = now - window_seconds

        window = self._windows[key]
        while window and window[0] < cutoff:
            window.popleft()

        if len(window) + cost <= max_requests:
            for _ in range(cost):
                window.append(now)
            remaining = max_requests - len(window)
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                reset_at=window[0] + window_seconds if window else now,
            )

        remaining = max_requests - len(window)
        wait = (window[0] + window_seconds - now) if window else 0.0
        return RateLimitResult(
            allowed=False,
            remaining=max(0, remaining),
            reset_at=now + wait,
            retry_after=wait,
        )

    async def reset(self, key: str) -> None:
        self._windows.pop(key, None)

    async def clear(self) -> None:
        self._windows.clear()
