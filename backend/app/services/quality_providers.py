from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseQualityProvider(ABC):
    """Interface for a third-party quality-check integration (plagiarism,
    AI-detection, publication-readiness, submission-assistant). Real
    providers plug in here by capability, keyed off a configured API key --
    see QualityCheckService. None of these integrations exist yet, so the
    only concrete implementation today is NotConfiguredProvider."""

    capability: str

    @abstractmethod
    async def check(self, text: str) -> dict[str, Any]: ...


class NotConfiguredProvider(BaseQualityProvider):
    """Returned for any capability with no provider wired up. Reports its
    own absence explicitly rather than a fake result or a "Coming Soon"
    placeholder -- the caller can tell the difference between "checked,
    nothing found" and "never actually checked."""

    def __init__(self, capability: str) -> None:
        self.capability = capability

    async def check(self, text: str) -> dict[str, Any]:
        return {
            "status": "not_configured",
            "capability": self.capability,
            "message": f"No provider is configured for {self.capability.replace('_', ' ')}.",
        }
