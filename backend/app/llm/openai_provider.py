from __future__ import annotations

from dataclasses import dataclass, field

from app.llm.provider import LLMResponse, ProviderConfig
from app.core.logging import get_logger

logger = get_logger("llm.openai")


@dataclass
class OpenAIProvider:
    """OpenAI LLM provider implementation.

    Uses the AsyncOpenAI client under the hood.
    """

    config: ProviderConfig = field(default_factory=lambda: ProviderConfig(model="gpt-4o"))

    def __post_init__(self) -> None:
        self._client: Any = None

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI()
        return self._client

    async def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return await self.generate_with_history(messages)

    async def generate_with_history(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        client = self._get_client()
        final_messages: list[dict[str, str]] = []
        if system_prompt:
            final_messages.append({"role": "system", "content": system_prompt})
        final_messages.extend(messages)

        response = await client.chat.completions.create(
            model=self.config.model,
            messages=final_messages,  # type: ignore[arg-type]
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            top_p=self.config.top_p,
            timeout=self.config.timeout_seconds,
        )

        choice = response.choices[0]
        usage_data = None
        if response.usage:
            usage_data = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        logger.info("openai generation complete", extra={
            "model": self.config.model,
            "usage": usage_data,
        })

        return LLMResponse(
            content=choice.message.content or "",
            model=self.config.model,
            usage=usage_data,
            finish_reason=choice.finish_reason,
        )

    async def count_tokens(self, text: str) -> int:
        import tiktoken
        encoding = tiktoken.encoding_for_model(self.config.model)
        return len(encoding.encode(text))
