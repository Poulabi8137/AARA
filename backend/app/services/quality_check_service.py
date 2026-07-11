from __future__ import annotations

from app.core.exceptions import ValidationError
from app.schemas.quality import QualityCapability, QualityCheckResponse
from app.services.quality_providers import BaseQualityProvider, NotConfiguredProvider


class QualityCheckService:
    """Phase 5 provider registry: one entry per future integration. Every
    capability currently resolves to NotConfiguredProvider since no real
    plagiarism/AI-detection/publication-readiness/submission-assistant
    integration exists in this codebase -- swapping in a real provider for
    a capability is a one-line change here once one is chosen, nothing
    else in the call chain needs to change."""

    def __init__(self) -> None:
        self._providers: dict[str, BaseQualityProvider] = {
            "plagiarism": NotConfiguredProvider("plagiarism"),
            "ai_detection": NotConfiguredProvider("ai_detection"),
            "publication_readiness": NotConfiguredProvider("publication_readiness"),
            "submission_assistant": NotConfiguredProvider("submission_assistant"),
        }

    async def run_check(
        self, capability: QualityCapability, text: str
    ) -> QualityCheckResponse:
        provider = self._providers.get(capability)
        if provider is None:
            raise ValidationError(f"Unknown quality capability: {capability}")
        result = await provider.check(text)
        return QualityCheckResponse(**result)
