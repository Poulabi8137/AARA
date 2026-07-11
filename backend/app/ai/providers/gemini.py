from __future__ import annotations

import json
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
from app.core.exceptions import ConfigurationError


class GeminiProvider(BaseLLMProvider):
    provider_id = "gemini"

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self._api_key = config.api_key or ""
        if not self._api_key:
            raise ConfigurationError("Gemini API key required", key="gemini_api_key")
        self._base_url = config.base_url or "https://generativelanguage.googleapis.com/v1beta"
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                params={"key": self._api_key},
                timeout=self.config.timeout,
            )
        return self._client

    async def chat(self, messages: list[LLMMessage]) -> LLMResponse:
        client = await self._get_client()
        contents = []
        system_instruction = None
        for m in messages:
            if m.role == "system":
                system_instruction = m.content
            else:
                role = "model" if m.role == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": m.content}]})

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        model_name = self.config.model.replace("gemini-", "").replace(".", "-")
        response = await client.post(f"/models/gemini-{model_name}:generateContent", json=payload)
        response.raise_for_status()
        data = response.json()

        candidates = data.get("candidates", [])
        content = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = " ".join(p.get("text", "") for p in parts)

        usage_data = data.get("usageMetadata", {})
        return LLMResponse(
            content=content,
            model=data.get("modelVersion", self.config.model),
            finish_reason=candidates[0].get("finishReason", "") if candidates else "",
            usage=LLMUsage(
                prompt_tokens=usage_data.get("promptTokenCount", 0),
                completion_tokens=usage_data.get("candidatesTokenCount", 0),
                total_tokens=usage_data.get("totalTokenCount", 0),
            ),
        )

    async def chat_stream(
        self, messages: list[LLMMessage]
    ) -> AsyncGenerator[LLMStreamEvent, None]:
        client = await self._get_client()
        contents = []
        system_instruction = None
        for m in messages:
            if m.role == "system":
                system_instruction = m.content
            else:
                role = "model" if m.role == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": m.content}]})

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        model_name = self.config.model.replace("gemini-", "").replace(".", "-")
        async with client.stream(
            "POST", f"/models/gemini-{model_name}:streamGenerateContent", json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = " ".join(p.get("text", "") for p in parts)
                    yield LLMStreamEvent(
                        content=text,
                        finish_reason=candidates[0].get("finishReason"),
                    )

    async def get_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(id="gemini-2.0-flash", provider="gemini"),
            ModelInfo(id="gemini-2.0-flash-lite", provider="gemini"),
            ModelInfo(id="gemini-1.5-flash", provider="gemini"),
            ModelInfo(id="gemini-1.5-pro", provider="gemini"),
        ]

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
            "gemini-2.0-flash": LLMCapabilities(
                max_context_tokens=1048576, max_output_tokens=8192,
                supports_streaming=True, supports_functions=True,
                supports_vision=True, supports_json_mode=True,
                cost_per_1k_input=0.0001, cost_per_1k_output=0.0004,
            ),
            "gemini-1.5-flash": LLMCapabilities(
                max_context_tokens=1048576, max_output_tokens=8192,
                supports_streaming=True, supports_functions=True,
                supports_vision=True, supports_json_mode=True,
                cost_per_1k_input=0.000075, cost_per_1k_output=0.0003,
            ),
            "gemini-1.5-pro": LLMCapabilities(
                max_context_tokens=2097152, max_output_tokens=8192,
                supports_streaming=True, supports_functions=True,
                supports_vision=True, supports_json_mode=True,
                cost_per_1k_input=0.00125, cost_per_1k_output=0.005,
            ),
        }
        return caps.get(model, LLMCapabilities(max_context_tokens=1048576, supports_streaming=True))
