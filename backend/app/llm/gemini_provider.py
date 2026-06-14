from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.llm.provider import LLMResponse, ProviderConfig
from app.core.logging import get_logger

logger = get_logger("llm.gemini")


@dataclass
class GeminiProvider:
    """Google Gemini LLM provider implementation."""

    config: ProviderConfig = field(default_factory=lambda: ProviderConfig(model="gemini-2.0-flash"))
    api_key: str | None = None

    def __post_init__(self) -> None:
        self._client: Any = None

    def _get_client(self):
        if self._client is None:
            try:
                import google.generativeai as genai
            except ImportError:
                raise ImportError("google-generativeai is required: pip install google-generativeai")
            genai.configure(api_key=self.api_key or "")
            self._client = genai.GenerativeModel(self.config.model)
        return self._client

    async def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        import google.generativeai as genai

        client = self._get_client()
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        response = await client.generate_content_async(full_prompt)

        usage_data = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage_data = {
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "completion_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count,
            }

        logger.info("gemini generation complete", extra={
            "model": self.config.model,
            "usage": usage_data,
        })

        return LLMResponse(
            content=response.text or "",
            model=self.config.model,
            usage=usage_data,
            finish_reason=str(response.candidates[0].finish_reason) if response.candidates else None,
        )

    async def generate_with_history(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        chat = self._get_client().start_chat()
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                response = await chat.send_message_async(content)

        return LLMResponse(
            content=response.text or "",
            model=self.config.model,
        )

    async def count_tokens(self, text: str) -> int:
        client = self._get_client()
        try:
            return client.count_tokens(text).total_tokens
        except Exception:
            return len(text.split())
