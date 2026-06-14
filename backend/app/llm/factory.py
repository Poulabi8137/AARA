from __future__ import annotations

import os
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.llm.provider import LLMProvider, ProviderConfig

logger = get_logger("llm.factory")

_PROVIDER_MAP: dict[str, str] = {
    "mock": "app.llm.mock_provider.MockProvider",
    "openai": "app.llm.openai_provider.OpenAIProvider",
    "gemini": "app.llm.gemini_provider.GeminiProvider",
}

_REQUIRED_API_KEYS: dict[str, str] = {
    "openai": "openai_api_key",
    "gemini": "gemini_api_key",
}


class ProviderInitError(RuntimeError):
    """Raised when provider initialisation fails."""


def get_llm_provider(settings: Settings) -> LLMProvider:
    """Factory: build an LLM provider from application settings.

    Selects the provider class by ``settings.llm_provider``, validates
        required API keys,
    and injects the configured model / temperature / max_tokens.

    Returns a fully initialised provider instance that satisfies the
        ``LLMProvider`` protocol.
    """
    provider_name = settings.llm_provider
    if provider_name not in _PROVIDER_MAP:
        raise ProviderInitError(
            f"Unknown LLM provider '{provider_name}'. "
            f"Supported: {', '.join(sorted(_PROVIDER_MAP))}",
        )

    _validate_api_key(provider_name, settings)

    config = ProviderConfig(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )

    provider = _build(provider_name, config, settings)
    logger.info(
        "llm provider initialised",
        extra={
            "provider": provider_name,
            "model": config.model,
            "temperature": config.temperature,
        },
    )
    return provider


def validate_provider_config(settings: Settings) -> list[str]:
    """Startup validation – returns a list of configuration errors.

    Call once at application startup to fail fast when the configured
    provider cannot be used.
    """
    errors: list[str] = []

    provider_name = settings.llm_provider
    if provider_name not in _PROVIDER_MAP:
        errors.append(
            f"LLM_PROVIDER='{provider_name}' is not supported. "
            f"Choose from: {', '.join(sorted(_PROVIDER_MAP))}",
        )
        return errors  # can't validate further

    key_name = _REQUIRED_API_KEYS.get(provider_name)
    if key_name:
        key_value = getattr(settings, key_name, "")
        if not key_value:
            errors.append(
                f"LLM_PROVIDER='{provider_name}' requires {key_name.upper()} "
                f"to be set in environment or .env",
            )

    if not settings.llm_model:
        errors.append("LLM_MODEL must not be empty")

    if not (0.0 <= settings.llm_temperature <= 2.0):
        errors.append("LLM_TEMPERATURE must be between 0.0 and 2.0")

    try:
        _build(provider_name, ProviderConfig(model=settings.llm_model), settings)
    except ProviderInitError as exc:
        errors.append(str(exc))

    return errors


# ── Internal helpers ────────────────────────────────────


def _validate_api_key(provider_name: str, settings: Settings) -> None:
    key_name = _REQUIRED_API_KEYS.get(provider_name)
    if not key_name:
        return
    key_value = getattr(settings, key_name, "")
    if not key_value:
        raise ProviderInitError(
            f"{key_name.upper()} is required when LLM_PROVIDER='{provider_name}'",
        )


def _build(
    provider_name: str,
    config: ProviderConfig,
    settings: Settings,
) -> LLMProvider:
    entry = _PROVIDER_MAP[provider_name]
    module_path, _, class_name = entry.rpartition(".")

    import importlib
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ProviderInitError(
            f"Failed to import provider module '{module_path}': {exc}",
        ) from exc

    cls = getattr(module, class_name, None)
    if cls is None:
        raise ProviderInitError(
            f"Provider class '{class_name}' not found in '{module_path}'",
        )

    try:
        if provider_name == "gemini":
            return cls(config=config, api_key=settings.gemini_api_key)
        return cls(config=config)
    except Exception as exc:
        raise ProviderInitError(
            f"Failed to initialise {provider_name} provider: {exc}",
        ) from exc
