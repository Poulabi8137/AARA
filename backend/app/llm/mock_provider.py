from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.llm.provider import LLMResponse, ProviderConfig


@dataclass
class MockProvider:
    """Mock LLM provider for testing and development.

    Returns predictable responses without calling any external API.
    """

    config: ProviderConfig = field(default_factory=lambda: ProviderConfig(model="mock"))
    response_delay_seconds: float = 0.05

    async def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        if self.response_delay_seconds > 0:
            import asyncio
            await asyncio.sleep(self.response_delay_seconds)

        return LLMResponse(
            content=f"[mock] Generated response for query (length={len(prompt)})",
            model="mock",
            usage={"prompt_tokens": len(prompt.split()), "completion_tokens": 50, "total_tokens": len(prompt.split()) + 50},
            finish_reason="stop",
        )

    async def generate_with_history(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        return await self.generate(
            prompt="\n".join(m.get("content", "") for m in messages),
            system_prompt=system_prompt,
        )

    async def count_tokens(self, text: str) -> int:
        return len(text.split())
