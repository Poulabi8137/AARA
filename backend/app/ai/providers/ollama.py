from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import httpx

from app.ai.providers.base import (
    BaseLLMProvider,
    LLMCapabilities,
    LLMConfig,
    LLMMessage,
    LLMResponse,
    LLMStreamEvent,
    LLMUsage,
    ModelInfo,
)


class OllamaProvider(BaseLLMProvider):
    provider_id = "ollama"

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self._base_url = config.base_url or "http://localhost:11434"
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self.config.timeout,
            )
        return self._client

    async def chat(self, messages: list[LLMMessage]) -> LLMResponse:
        client = await self._get_client()
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }
        if self.config.stop:
            payload["options"]["stop"] = self.config.stop

        response = await client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data.get("message", {}).get("content", ""),
            model=data.get("model", self.config.model),
            finish_reason=data.get("done_reason", ""),
            usage=LLMUsage(
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                total_tokens=(data.get("prompt_eval_count", 0) + data.get("eval_count", 0)),
            ),
        )

    async def chat_stream(
        self, messages: list[LLMMessage]
    ) -> AsyncGenerator[LLMStreamEvent, None]:
        client = await self._get_client()
        payload = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
            "stream": True,
        }
        async with client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    import json
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                message = data.get("message", {})
                yield LLMStreamEvent(
                    content=message.get("content", ""),
                    finish_reason=data.get("done_reason"),
                )

    async def get_models(self) -> list[ModelInfo]:
        client = await self._get_client()
        response = await client.get("/api/tags")
        response.raise_for_status()
        data = response.json()
        return [ModelInfo(id=m["name"], provider="ollama") for m in data.get("models", [])]

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            return response.is_success
        except Exception:
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def get_capabilities(model: str) -> LLMCapabilities:
        return LLMCapabilities(
            max_context_tokens=32768, max_output_tokens=4096,
            supports_streaming=True, supports_json_mode=True,
            cost_per_1k_input=0.0, cost_per_1k_output=0.0,
        )
