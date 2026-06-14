from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict[str, int] | None = None
    finish_reason: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ProviderConfig:
    model: str = "gpt-4o"
    temperature: float = 0.0
    max_tokens: int = 4096
    top_p: float = 1.0
    timeout_seconds: int = 60


@runtime_checkable
class LLMProvider(Protocol):
    """Abstract interface for all LLM providers.

    Any provider (OpenAI, Gemini, Anthropic, local) that implements
    this protocol can be plugged into the agent workflow without
    changing orchestration code.
    """

    config: ProviderConfig

    async def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        ...

    async def generate_with_history(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        ...

    async def count_tokens(self, text: str) -> int:
        ...
