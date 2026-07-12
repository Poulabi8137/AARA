from __future__ import annotations


from app.core.config import get_settings
from app.core.logging import get_logger
from app.llm.factory import get_llm_provider
from app.llm.provider import LLMProvider, ProviderConfig
from app.rag.config import get_rag_settings

logger = get_logger("rag.llm")
settings = get_settings()
rag_settings = get_rag_settings()


class RAGLLMProvider:
    def __init__(self, provider: LLMProvider | None = None):
        self._provider = provider or get_llm_provider(settings)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        if temperature is not None or max_tokens is not None:
            original_config = self._provider.config
            override = ProviderConfig(
                model=original_config.model,
                temperature=temperature
                if temperature is not None
                else original_config.temperature,
                max_tokens=max_tokens
                if max_tokens is not None
                else original_config.max_tokens,
                top_p=original_config.top_p,
                timeout_seconds=original_config.timeout_seconds,
            )
            provider_override = self._clone_with_config(override)
            response = await provider_override.generate(
                prompt, system_prompt=system_prompt
            )
        else:
            response = await self._provider.generate(
                prompt, system_prompt=system_prompt
            )

        content = response.content.strip()
        logger.info(
            "llm generation",
            extra={
                "model": response.model,
                "prompt_length": len(prompt),
                "response_length": len(content),
                "usage": response.usage,
            },
        )
        return content

    async def generate_with_history(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> str:
        response = await self._provider.generate_with_history(
            messages, system_prompt=system_prompt
        )
        return response.content.strip()

    async def count_tokens(self, text: str) -> int:
        return await self._provider.count_tokens(text)

    def _clone_with_config(self, config: ProviderConfig) -> LLMProvider:
        provider_name = settings.llm_provider
        if provider_name == "openai":
            from app.llm.openai_provider import OpenAIProvider

            return OpenAIProvider(config=config)
        if provider_name == "gemini":
            from app.llm.gemini_provider import GeminiProvider

            return GeminiProvider(config=config, api_key=settings.gemini_api_key)
        from app.llm.mock_provider import MockProvider

        return MockProvider(config=config)
