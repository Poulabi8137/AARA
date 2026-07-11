from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMMessage:
    role: str  # system, user, assistant, tool
    content: str
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


@dataclass
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    content: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    model: str = ""
    finish_reason: str = ""
    tool_calls: list[dict[str, Any]] | None = None


@dataclass
class LLMStreamEvent:
    content: str = ""
    finish_reason: str | None = None
    usage: LLMUsage | None = None


@dataclass
class LLMConfig:
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: list[str] | None = None
    timeout: float = 60.0
    max_retries: int = 3
    api_key: str | None = None
    base_url: str | None = None
    organization: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMCapabilities:
    max_context_tokens: int = 0
    max_output_tokens: int = 0
    supports_streaming: bool = False
    supports_functions: bool = False
    supports_vision: bool = False
    supports_json_mode: bool = False
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0


@dataclass
class ModelInfo:
    id: str
    provider: str
    capabilities: LLMCapabilities = field(default_factory=LLMCapabilities)


class BaseLLMProvider(ABC):
    provider_id: str = ""
    model: str = ""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @abstractmethod
    async def chat(self, messages: list[LLMMessage]) -> LLMResponse:
        ...

    @abstractmethod
    async def chat_stream(
        self, messages: list[LLMMessage]
    ) -> AsyncGenerator[LLMStreamEvent, None]:
        yield LLMStreamEvent()

    @abstractmethod
    async def get_models(self) -> list[ModelInfo]:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...

    async def count_tokens(self, messages: list[LLMMessage]) -> int:
        return sum(len(m.content) // 4 for m in messages)

    async def close(self) -> None:
        return None
