from __future__ import annotations

import json
from collections.abc import AsyncGenerator

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
from app.core.exceptions import ConfigurationError


class GroqProvider(BaseLLMProvider):
    provider_id = "groq"

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self._api_key = config.api_key or ""
        if not self._api_key:
            raise ConfigurationError("Groq API key required", key="groq_api_key")
        self._base_url = config.base_url or "https://api.groq.com/openai/v1"
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.config.timeout,
            )
        return self._client

    async def chat(self, messages: list[LLMMessage]) -> LLMResponse:
        client = await self._get_client()
        payload = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise ValueError("Groq response contained no choices")
        choice = choices[0]
        usage_data = data.get("usage", {})
        return LLMResponse(
            content=choice["message"]["content"] or "",
            model=data["model"],
            finish_reason=choice.get("finish_reason", ""),
            usage=LLMUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            ),
        )

    async def chat_stream(
        self, messages: list[LLMMessage]
    ) -> AsyncGenerator[LLMStreamEvent, None]:
        client = await self._get_client()
        payload = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": True,
        }
        async with client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                choice = data.get("choices", [{}])[0]
                delta = choice.get("delta", {})
                yield LLMStreamEvent(
                    content=delta.get("content", ""),
                    finish_reason=choice.get("finish_reason"),
                )

    async def get_models(self) -> list[ModelInfo]:
        client = await self._get_client()
        response = await client.get("/models")
        response.raise_for_status()
        data = response.json()
        return [ModelInfo(id=m["id"], provider="groq") for m in data.get("data", [])]

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/models")
            return response.is_success
        except Exception:
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def get_capabilities(model: str) -> LLMCapabilities:
        caps = {
            "llama-3.3-70b-versatile": LLMCapabilities(
                max_context_tokens=32768, max_output_tokens=8192,
                supports_streaming=True, supports_functions=True,
                supports_json_mode=True,
                cost_per_1k_input=0.00059, cost_per_1k_output=0.00079,
            ),
            "llama-3.1-8b-instant": LLMCapabilities(
                max_context_tokens=8192, max_output_tokens=8192,
                supports_streaming=True, supports_functions=True,
                supports_json_mode=True,
                cost_per_1k_input=0.00005, cost_per_1k_output=0.00008,
            ),
            "mixtral-8x7b-32768": LLMCapabilities(
                max_context_tokens=32768, max_output_tokens=4096,
                supports_streaming=True, supports_functions=True,
                supports_json_mode=True,
                cost_per_1k_input=0.00024, cost_per_1k_output=0.00024,
            ),
            "gemma2-9b-it": LLMCapabilities(
                max_context_tokens=8192, max_output_tokens=4096,
                supports_streaming=True, supports_json_mode=True,
                cost_per_1k_input=0.00010, cost_per_1k_output=0.00010,
            ),
        }
        return caps.get(model, LLMCapabilities(max_context_tokens=8192, supports_streaming=True))
