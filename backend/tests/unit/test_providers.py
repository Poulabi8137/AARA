from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx
import pytest

from app.ai.providers.base import (
    BaseLLMProvider,
    LLMCapabilities,
    LLMConfig,
    LLMMessage,
    LLMResponse,
    LLMStreamEvent,
    ModelInfo,
)
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.groq import GroqProvider
from app.ai.providers.ollama import OllamaProvider
from app.ai.providers.openai import OpenAIProvider
from app.ai.providers.openrouter import OpenRouterProvider
from app.ai.providers.router import (
    ProviderRouter,
    RoutingResult,
    SelectionCriteria,
)
from app.core.exceptions import ConfigurationError

# ---------------------------------------------------------------------------
# Mock HTTP helpers
# ---------------------------------------------------------------------------

class MockResponse:
    def __init__(self, status_code: int = 200, json_data: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._json_data = json_data or {}
        self._text = text
        self.is_success = 200 <= status_code < 300

    def raise_for_status(self) -> None:
        if not self.is_success:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=httpx.Request("POST", "http://mock"),
                response=self,
            )

    def json(self) -> dict:
        return self._json_data

    def aiter_lines(self):
        return _AsyncLineIter(self._text.split("\n") if self._text else [])


class _AsyncLineIter:
    def __init__(self, lines: list[str]) -> None:
        self._lines = iter(lines)

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        try:
            value = next(self._lines)
            if value:
                return value
            return await self.__anext__()
        except StopIteration:
            raise StopAsyncIteration


class MockStreamContext:
    def __init__(self, response: MockResponse) -> None:
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    def raise_for_status(self) -> None:
        self._response.raise_for_status()

    def aiter_lines(self):
        return self._response.aiter_lines()


class MockAsyncClient:
    def __init__(self, **kwargs: Any) -> None:
        self._responses: list[MockResponse] = []
        self._stream_responses: list[MockResponse] = []
        self._call_count = 0
        self._stream_call_count = 0
        self._last_request: dict | None = None
        self.aclose_called = False

    def add_response(self, resp: MockResponse) -> None:
        self._responses.append(resp)

    def add_stream_response(self, resp: MockResponse) -> None:
        self._stream_responses.append(resp)

    async def get(self, url: str, **kwargs: Any) -> MockResponse:
        return self._next_response("GET", url)

    async def post(self, url: str, json: dict | None = None, **kwargs: Any) -> MockResponse:
        self._last_request = json
        return self._next_response("POST", url)

    def stream(self, method: str, url: str, **kwargs: Any) -> MockStreamContext:
        idx = self._stream_call_count
        self._stream_call_count += 1
        if idx < len(self._stream_responses):
            return MockStreamContext(self._stream_responses[idx])
        return MockStreamContext(MockResponse(200))

    def _next_response(self, method: str, url: str) -> MockResponse:
        idx = self._call_count
        self._call_count += 1
        if idx < len(self._responses):
            return self._responses[idx]
        return MockResponse(200, {})

    async def aclose(self) -> None:
        self.aclose_called = True


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def openai_config() -> LLMConfig:
    return LLMConfig(api_key="sk-test", model="gpt-4o-mini")


@pytest.fixture
def gemini_config() -> LLMConfig:
    return LLMConfig(api_key="ai-test-key", model="gemini-1.5-flash")


@pytest.fixture
def groq_config() -> LLMConfig:
    return LLMConfig(api_key="gsk-test", model="llama-3.1-8b-instant")


@pytest.fixture
def openrouter_config() -> LLMConfig:
    return LLMConfig(api_key="or-test", model="gpt-4o-mini")


@pytest.fixture
def ollama_config() -> LLMConfig:
    return LLMConfig(model="llama3.2")


@pytest.fixture
def sample_messages() -> list[LLMMessage]:
    return [
        LLMMessage(role="system", content="You are a helpful assistant."),
        LLMMessage(role="user", content="Hello!"),
    ]


# ---------------------------------------------------------------------------
# Helper: monkey-patch _get_client on a provider
# ---------------------------------------------------------------------------

def patch_client(provider_cls, monkeypatch, client: MockAsyncClient):
    async def _fake_get_client(*args, **kwargs):
        return client
    monkeypatch.setattr(provider_cls, "_get_client", _fake_get_client)


# ---------------------------------------------------------------------------
# Helper: minimal concrete subclass of BaseLLMProvider
# ---------------------------------------------------------------------------

def make_concrete_provider(**overrides: Any) -> BaseLLMProvider:
    class _Concrete(BaseLLMProvider):
        provider_id = overrides.get("provider_id", "test")
        model = overrides.get("model", "test-model")

        async def chat(self, messages: list[LLMMessage]) -> LLMResponse:
            return overrides.get("chat_return", LLMResponse(content=""))

        async def chat_stream(
            self, messages: list[LLMMessage]
        ) -> AsyncGenerator[LLMStreamEvent, None]:
            yield overrides.get("stream_return", LLMStreamEvent())

        async def get_models(self) -> list[ModelInfo]:
            return overrides.get("models_return", [])

        async def health_check(self) -> bool:
            return overrides.get("health_return", True)

    return _Concrete(LLMConfig())


# ===================================================================
# BaseLLMProvider
# ===================================================================

class TestBaseLLMProvider:
    async def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseLLMProvider(LLMConfig())  # type: ignore[abstract]

    async def test_count_tokens_approximates_by_character_length(self):
        messages = [
            LLMMessage(role="user", content="hello world"),
            LLMMessage(role="assistant", content="hi there!"),
        ]
        provider = make_concrete_provider()
        count = await provider.count_tokens(messages)
        assert count == 4  # 11//4 + 9//4

    async def test_count_tokens_empty_messages(self):
        provider = make_concrete_provider()
        assert await provider.count_tokens([]) == 0

    async def test_count_tokens_long_content(self):
        provider = make_concrete_provider()
        messages = [LLMMessage(role="user", content="a" * 100)]
        assert await provider.count_tokens(messages) == 25

    async def test_close_returns_none(self):
        provider = make_concrete_provider()
        assert await provider.close() is None


# ===================================================================
# OpenAIProvider
# ===================================================================

class TestOpenAIProvider:
    def test_init_missing_api_key_raises(self):
        with pytest.raises(ConfigurationError, match="OpenAI API key required"):
            OpenAIProvider(LLMConfig(api_key=""))

    def test_init_with_api_key_succeeds(self, openai_config):
        provider = OpenAIProvider(openai_config)
        assert provider.provider_id == "openai"

    @pytest.mark.asyncio
    async def test_chat_returns_llm_response(self, openai_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "id": "chatcmpl-123",
            "model": "gpt-4o-mini",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hello!"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }))
        patch_client(OpenAIProvider, monkeypatch, client)

        provider = OpenAIProvider(openai_config)
        response = await provider.chat(sample_messages)

        assert isinstance(response, LLMResponse)
        assert response.content == "Hello!"
        assert response.model == "gpt-4o-mini"
        assert response.finish_reason == "stop"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 5
        assert response.usage.total_tokens == 15
        assert client._last_request["model"] == "gpt-4o-mini"
        assert client._last_request["messages"] == [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]

    @pytest.mark.asyncio
    async def test_chat_http_error_raises(self, openai_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(401, {"error": "unauthorized"}))
        patch_client(OpenAIProvider, monkeypatch, client)

        provider = OpenAIProvider(openai_config)
        with pytest.raises(httpx.HTTPStatusError):
            await provider.chat(sample_messages)

    @pytest.mark.asyncio
    async def test_chat_empty_choices_raises_value_error(self, openai_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "id": "cmpl-empty",
            "model": "gpt-4o-mini",
            "choices": [],
        }))
        patch_client(OpenAIProvider, monkeypatch, client)

        provider = OpenAIProvider(openai_config)
        with pytest.raises(ValueError, match="no choices"):
            await provider.chat(sample_messages)

    @pytest.mark.asyncio
    async def test_chat_without_usage_data_defaults_to_zero(self, openai_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "id": "cmpl-1",
            "model": "gpt-4o-mini",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hi"}, "finish_reason": "stop"}],
        }))
        patch_client(OpenAIProvider, monkeypatch, client)

        provider = OpenAIProvider(openai_config)
        response = await provider.chat(sample_messages)
        assert response.usage.total_tokens == 0

    @pytest.mark.asyncio
    async def test_chat_with_stop_in_payload(self, openai_config, sample_messages, monkeypatch):
        openai_config.stop = ["\n\n", "stop"]
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "id": "cmpl-2",
            "model": "gpt-4o-mini",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "OK"}, "finish_reason": "stop"}],
            "usage": {},
        }))
        patch_client(OpenAIProvider, monkeypatch, client)

        provider = OpenAIProvider(openai_config)
        await provider.chat(sample_messages)
        assert client._last_request["stop"] == ["\n\n", "stop"]

    @pytest.mark.asyncio
    async def test_chat_with_tool_calls(self, openai_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "id": "cmpl-3",
            "model": "gpt-4o-mini",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "get_weather", "arguments": "{}"}}],
                },
                "finish_reason": "tool_calls",
            }],
            "usage": {},
        }))
        patch_client(OpenAIProvider, monkeypatch, client)

        provider = OpenAIProvider(openai_config)
        response = await provider.chat(sample_messages)
        assert response.content == ""
        assert response.finish_reason == "tool_calls"
        assert response.tool_calls is not None
        assert response.tool_calls[0]["function"]["name"] == "get_weather"

    @pytest.mark.asyncio
    async def test_chat_stream_yields_events(self, openai_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_stream_response(MockResponse(200, text="\n".join([
            'data: {"choices":[{"delta":{"content":"Hello"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":" world"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ])))
        patch_client(OpenAIProvider, monkeypatch, client)

        provider = OpenAIProvider(openai_config)
        events = [e async for e in provider.chat_stream(sample_messages)]
        assert len(events) == 3
        assert events[0].content == "Hello"
        assert events[1].content == " world"
        assert events[2].finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_chat_stream_skips_invalid_json(self, openai_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_stream_response(MockResponse(200, text="\n".join([
            'data: {"choices":[{"delta":{"content":"Hi"}}]}',
            "data: not-json",
            "data: [DONE]",
        ])))
        patch_client(OpenAIProvider, monkeypatch, client)

        provider = OpenAIProvider(openai_config)
        events = [e async for e in provider.chat_stream(sample_messages)]
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_chat_stream_skips_non_data_lines(self, openai_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_stream_response(MockResponse(200, text="\n".join([
            ': heartbeat',
            'data: {"choices":[{"delta":{"content":"Hi"}}]}',
            "data: [DONE]",
        ])))
        patch_client(OpenAIProvider, monkeypatch, client)

        provider = OpenAIProvider(openai_config)
        events = [e async for e in provider.chat_stream(sample_messages)]
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_get_models_returns_list(self, openai_config, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "object": "list",
            "data": [{"id": "gpt-4o", "object": "model"}, {"id": "gpt-4o-mini", "object": "model"}],
        }))
        patch_client(OpenAIProvider, monkeypatch, client)

        provider = OpenAIProvider(openai_config)
        models = await provider.get_models()
        assert len(models) == 2
        assert models[0].id == "gpt-4o"
        assert models[0].provider == "openai"

    @pytest.mark.asyncio
    async def test_health_check_returns_true_on_success(self, openai_config, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200))
        patch_client(OpenAIProvider, monkeypatch, client)

        provider = OpenAIProvider(openai_config)
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_http_error(self, openai_config, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(500))
        patch_client(OpenAIProvider, monkeypatch, client)

        provider = OpenAIProvider(openai_config)
        assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_exception(self, openai_config, monkeypatch):
        async def _fail(*args, **kwargs):
            raise ConnectionError("network error")
        monkeypatch.setattr(OpenAIProvider, "_get_client", _fail)

        provider = OpenAIProvider(openai_config)
        assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_close_cleans_up_client(self, openai_config, monkeypatch):
        client = MockAsyncClient()
        patch_client(OpenAIProvider, monkeypatch, client)

        provider = OpenAIProvider(openai_config)
        provider._client = client
        await provider.close()
        assert client.aclose_called

    @pytest.mark.asyncio
    async def test_close_when_no_client(self, openai_config):
        provider = OpenAIProvider(openai_config)
        await provider.close()

    def test_get_capabilities_known_model(self):
        caps = OpenAIProvider.get_capabilities("gpt-4o")
        assert caps.supports_streaming is True
        assert caps.supports_functions is True
        assert caps.supports_vision is True
        assert caps.max_context_tokens == 128000
        assert caps.cost_per_1k_input == 0.0025

    def test_get_capabilities_unknown_model_returns_default(self):
        caps = OpenAIProvider.get_capabilities("unknown-model")
        assert caps.supports_streaming is True
        assert caps.supports_functions is False
        assert caps.max_context_tokens == 8192


# ===================================================================
# GeminiProvider
# ===================================================================

class TestGeminiProvider:
    def test_init_missing_api_key_raises(self):
        with pytest.raises(ConfigurationError, match="Gemini API key required"):
            GeminiProvider(LLMConfig(api_key=""))

    def test_init_with_api_key_succeeds(self, gemini_config):
        provider = GeminiProvider(gemini_config)
        assert provider.provider_id == "gemini"

    @pytest.mark.asyncio
    async def test_chat_constructs_correct_payload(self, gemini_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "candidates": [{"content": {"parts": [{"text": "Hello!"}]}, "finishReason": "STOP"}],
            "modelVersion": "gemini-1.5-flash",
            "usageMetadata": {"promptTokenCount": 8, "candidatesTokenCount": 4, "totalTokenCount": 12},
        }))
        patch_client(GeminiProvider, monkeypatch, client)

        provider = GeminiProvider(gemini_config)
        response = await provider.chat(sample_messages)

        assert response.content == "Hello!"
        assert response.model == "gemini-1.5-flash"
        assert response.finish_reason == "STOP"
        assert response.usage.prompt_tokens == 8
        assert response.usage.completion_tokens == 4
        assert response.usage.total_tokens == 12
        assert "systemInstruction" in client._last_request
        assert client._last_request["systemInstruction"]["parts"][0]["text"] == "You are a helpful assistant."
        assert client._last_request["contents"] == [{"role": "user", "parts": [{"text": "Hello!"}]}]

    @pytest.mark.asyncio
    async def test_chat_converts_assistant_role_to_model(self, gemini_config, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "candidates": [{"content": {"parts": [{"text": "OK"}]}, "finishReason": "STOP"}],
            "modelVersion": "gemini-1.5-flash",
            "usageMetadata": {},
        }))
        patch_client(GeminiProvider, monkeypatch, client)

        provider = GeminiProvider(gemini_config)
        messages = [
            LLMMessage(role="user", content="Hi"),
            LLMMessage(role="assistant", content="Hello"),
        ]
        await provider.chat(messages)
        assert client._last_request["contents"][0]["role"] == "user"
        assert client._last_request["contents"][1]["role"] == "model"

    @pytest.mark.asyncio
    async def test_chat_no_system_message_in_payload(self, gemini_config, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "candidates": [{"content": {"parts": [{"text": "OK"}]}, "finishReason": "STOP"}],
            "modelVersion": "gemini-1.5-flash",
            "usageMetadata": {},
        }))
        patch_client(GeminiProvider, monkeypatch, client)

        provider = GeminiProvider(gemini_config)
        await provider.chat([LLMMessage(role="user", content="Hi")])
        assert "systemInstruction" not in client._last_request

    @pytest.mark.asyncio
    async def test_chat_no_candidates_returns_empty_content(self, gemini_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "candidates": [],
            "modelVersion": "gemini-1.5-flash",
            "usageMetadata": {},
        }))
        patch_client(GeminiProvider, monkeypatch, client)

        provider = GeminiProvider(gemini_config)
        response = await provider.chat(sample_messages)
        assert response.content == ""
        assert response.finish_reason == ""

    @pytest.mark.asyncio
    async def test_chat_stream_yields_events(self, gemini_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_stream_response(MockResponse(200, text="\n".join([
            json.dumps({"candidates": [{"content": {"parts": [{"text": "Hello"}]}, "finishReason": None}]}),
            json.dumps({"candidates": [{"content": {"parts": [{"text": " world"}]}, "finishReason": None}]}),
            json.dumps({"candidates": [{"content": {"parts": [{"text": ""}]}, "finishReason": "STOP"}]}),
        ])))
        patch_client(GeminiProvider, monkeypatch, client)

        provider = GeminiProvider(gemini_config)
        events = [e async for e in provider.chat_stream(sample_messages)]
        assert len(events) == 3
        assert events[0].content == "Hello"
        assert events[1].content == " world"
        assert events[2].finish_reason == "STOP"

    @pytest.mark.asyncio
    async def test_chat_stream_skips_empty_lines(self, gemini_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_stream_response(MockResponse(200, text="\n\n" + json.dumps({
            "candidates": [{"content": {"parts": [{"text": "Hi"}]}, "finishReason": None}],
        }) + "\n"))
        patch_client(GeminiProvider, monkeypatch, client)

        provider = GeminiProvider(gemini_config)
        events = [e async for e in provider.chat_stream(sample_messages)]
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_get_models_returns_hardcoded_list(self, gemini_config):
        provider = GeminiProvider(gemini_config)
        models = await provider.get_models()
        assert len(models) == 4
        assert models[0].id == "gemini-2.0-flash"
        assert models[3].id == "gemini-1.5-pro"

    @pytest.mark.asyncio
    async def test_health_check_success(self, gemini_config, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200))
        patch_client(GeminiProvider, monkeypatch, client)

        provider = GeminiProvider(gemini_config)
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, gemini_config, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(500))
        patch_client(GeminiProvider, monkeypatch, client)

        provider = GeminiProvider(gemini_config)
        assert await provider.health_check() is False

    def test_get_capabilities_known_model(self):
        caps = GeminiProvider.get_capabilities("gemini-1.5-pro")
        assert caps.max_context_tokens == 2097152
        assert caps.cost_per_1k_input == 0.00125

    def test_get_capabilities_unknown_model(self):
        caps = GeminiProvider.get_capabilities("unknown")
        assert caps.max_context_tokens == 1048576
        assert caps.supports_streaming is True


# ===================================================================
# GroqProvider
# ===================================================================

class TestGroqProvider:
    def test_init_missing_api_key_raises(self):
        with pytest.raises(ConfigurationError, match="Groq API key required"):
            GroqProvider(LLMConfig(api_key=""))

    def test_init_with_api_key_succeeds(self, groq_config):
        provider = GroqProvider(groq_config)
        assert provider.provider_id == "groq"

    @pytest.mark.asyncio
    async def test_chat_returns_response(self, groq_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "id": "groq-cmpl-1",
            "model": "llama-3.1-8b-instant",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "Groq reply"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 6, "total_tokens": 18},
        }))
        patch_client(GroqProvider, monkeypatch, client)

        provider = GroqProvider(groq_config)
        response = await provider.chat(sample_messages)

        assert response.content == "Groq reply"
        assert response.model == "llama-3.1-8b-instant"
        assert response.finish_reason == "stop"
        assert response.usage.total_tokens == 18
        assert client._last_request["model"] == "llama-3.1-8b-instant"

    @pytest.mark.asyncio
    async def test_chat_empty_choices_raises_value_error(self, groq_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "id": "groq-cmpl-empty",
            "model": "llama-3.1-8b-instant",
            "choices": [],
        }))
        patch_client(GroqProvider, monkeypatch, client)

        provider = GroqProvider(groq_config)
        with pytest.raises(ValueError, match="no choices"):
            await provider.chat(sample_messages)

    @pytest.mark.asyncio
    async def test_chat_stream_yields_events(self, groq_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_stream_response(MockResponse(200, text="\n".join([
            'data: {"choices":[{"delta":{"content":"Hi"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ])))
        patch_client(GroqProvider, monkeypatch, client)

        provider = GroqProvider(groq_config)
        events = [e async for e in provider.chat_stream(sample_messages)]
        assert len(events) == 2
        assert events[0].content == "Hi"

    @pytest.mark.asyncio
    async def test_get_models_returns_list(self, groq_config, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "object": "list",
            "data": [{"id": "llama-3.1-8b-instant", "object": "model"}],
        }))
        patch_client(GroqProvider, monkeypatch, client)

        provider = GroqProvider(groq_config)
        models = await provider.get_models()
        assert len(models) == 1
        assert models[0].provider == "groq"

    @pytest.mark.asyncio
    async def test_health_check_success(self, groq_config, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200))
        patch_client(GroqProvider, monkeypatch, client)

        provider = GroqProvider(groq_config)
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, groq_config, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(503))
        patch_client(GroqProvider, monkeypatch, client)

        provider = GroqProvider(groq_config)
        assert await provider.health_check() is False

    def test_get_capabilities_known_model(self):
        caps = GroqProvider.get_capabilities("llama-3.3-70b-versatile")
        assert caps.max_context_tokens == 32768
        assert caps.supports_functions is True

    def test_get_capabilities_unknown_model(self):
        caps = GroqProvider.get_capabilities("unknown")
        assert caps.max_context_tokens == 8192


# ===================================================================
# OpenRouterProvider
# ===================================================================

class TestOpenRouterProvider:
    def test_init_missing_api_key_raises(self):
        with pytest.raises(ConfigurationError, match="OpenRouter API key required"):
            OpenRouterProvider(LLMConfig(api_key=""))

    def test_init_with_api_key_succeeds(self, openrouter_config):
        provider = OpenRouterProvider(openrouter_config)
        assert provider.provider_id == "openrouter"

    @pytest.mark.asyncio
    async def test_chat_returns_response(self, openrouter_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "id": "or-cmpl-1",
            "model": "gpt-4o-mini",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "OR reply"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        }))
        patch_client(OpenRouterProvider, monkeypatch, client)

        provider = OpenRouterProvider(openrouter_config)
        response = await provider.chat(sample_messages)

        assert response.content == "OR reply"
        assert response.model == "gpt-4o-mini"
        assert response.usage.total_tokens == 8

    @pytest.mark.asyncio
    async def test_chat_empty_choices_raises_value_error(self, openrouter_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "id": "or-cmpl-empty",
            "model": "gpt-4o-mini",
            "choices": [],
        }))
        patch_client(OpenRouterProvider, monkeypatch, client)

        provider = OpenRouterProvider(openrouter_config)
        with pytest.raises(ValueError, match="no choices"):
            await provider.chat(sample_messages)

    @pytest.mark.asyncio
    async def test_chat_with_stop_sequences(self, openrouter_config, sample_messages, monkeypatch):
        openrouter_config.stop = ["<stop>"]
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "id": "or-cmpl-2",
            "model": "gpt-4o-mini",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "OK"}, "finish_reason": "stop"}],
            "usage": {},
        }))
        patch_client(OpenRouterProvider, monkeypatch, client)

        provider = OpenRouterProvider(openrouter_config)
        await provider.chat(sample_messages)
        assert client._last_request["stop"] == ["<stop>"]

    @pytest.mark.asyncio
    async def test_chat_with_referrer_and_title_headers(self, monkeypatch):
        config = LLMConfig(
            api_key="or-test",
            model="gpt-4o-mini",
            extra={"referrer": "https://example.com", "title": "MyApp"},
        )
        provider = OpenRouterProvider(config)
        assert provider._base_url == "https://openrouter.ai/api/v1"

    @pytest.mark.asyncio
    async def test_chat_stream_yields_events(self, openrouter_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_stream_response(MockResponse(200, text="\n".join([
            'data: {"choices":[{"delta":{"content":"Hi"},"finish_reason":null}]}',
            "data: [DONE]",
        ])))
        patch_client(OpenRouterProvider, monkeypatch, client)

        provider = OpenRouterProvider(openrouter_config)
        events = [e async for e in provider.chat_stream(sample_messages)]
        assert len(events) == 1
        assert events[0].content == "Hi"

    @pytest.mark.asyncio
    async def test_get_models_returns_list(self, openrouter_config, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "data": [{"id": "gpt-4o", "object": "model"}],
        }))
        patch_client(OpenRouterProvider, monkeypatch, client)

        provider = OpenRouterProvider(openrouter_config)
        models = await provider.get_models()
        assert len(models) == 1
        assert models[0].provider == "openrouter"

    @pytest.mark.asyncio
    async def test_health_check_success(self, openrouter_config, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200))
        patch_client(OpenRouterProvider, monkeypatch, client)

        provider = OpenRouterProvider(openrouter_config)
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, openrouter_config, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(400))
        patch_client(OpenRouterProvider, monkeypatch, client)

        provider = OpenRouterProvider(openrouter_config)
        assert await provider.health_check() is False

    def test_get_capabilities_always_returns_default(self):
        caps = OpenRouterProvider.get_capabilities("any-model")
        assert caps.max_context_tokens == 128000
        assert caps.supports_streaming is True
        assert caps.supports_functions is True
        assert caps.cost_per_1k_input == 0.0


# ===================================================================
# OllamaProvider
# ===================================================================

class TestOllamaProvider:
    def test_init_no_api_key_needed(self):
        provider = OllamaProvider(LLMConfig())
        assert provider.provider_id == "ollama"
        assert provider._base_url == "http://localhost:11434"

    @pytest.mark.asyncio
    async def test_chat_returns_response(self, ollama_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "model": "llama3.2",
            "message": {"role": "assistant", "content": "Ollama reply"},
            "done_reason": "stop",
            "prompt_eval_count": 8,
            "eval_count": 4,
        }))
        patch_client(OllamaProvider, monkeypatch, client)

        provider = OllamaProvider(ollama_config)
        response = await provider.chat(sample_messages)

        assert response.content == "Ollama reply"
        assert response.model == "llama3.2"
        assert response.finish_reason == "stop"
        assert response.usage.prompt_tokens == 8
        assert response.usage.completion_tokens == 4
        assert response.usage.total_tokens == 12
        assert client._last_request["model"] == "llama3.2"
        assert client._last_request["options"]["temperature"] == 0.7
        assert client._last_request["options"]["num_predict"] == 4096

    @pytest.mark.asyncio
    async def test_chat_with_stop_sequence(self, ollama_config, sample_messages, monkeypatch):
        ollama_config.stop = ["\n", "stop"]
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "model": "llama3.2",
            "message": {"role": "assistant", "content": "OK"},
            "done_reason": "stop",
        }))
        patch_client(OllamaProvider, monkeypatch, client)

        provider = OllamaProvider(ollama_config)
        await provider.chat(sample_messages)
        assert client._last_request["options"]["stop"] == ["\n", "stop"]

    @pytest.mark.asyncio
    async def test_chat_missing_message_field_returns_empty(self, ollama_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "model": "llama3.2",
            "done_reason": "stop",
        }))
        patch_client(OllamaProvider, monkeypatch, client)

        provider = OllamaProvider(ollama_config)
        response = await provider.chat(sample_messages)
        assert response.content == ""

    @pytest.mark.asyncio
    async def test_chat_stream_yields_events(self, ollama_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_stream_response(MockResponse(200, text="\n".join([
            json.dumps({"message": {"content": "Hello"}, "done_reason": None}),
            json.dumps({"message": {"content": " world"}, "done_reason": "stop"}),
        ])))
        patch_client(OllamaProvider, monkeypatch, client)

        provider = OllamaProvider(ollama_config)
        events = [e async for e in provider.chat_stream(sample_messages)]
        assert len(events) == 2
        assert events[0].content == "Hello"
        assert events[1].finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_chat_stream_skips_empty_lines_and_invalid_json(self, ollama_config, sample_messages, monkeypatch):
        client = MockAsyncClient()
        client.add_stream_response(MockResponse(200, text="\n".join([
            "",
            "not-json",
            json.dumps({"message": {"content": "Hi"}, "done_reason": None}),
        ])))
        patch_client(OllamaProvider, monkeypatch, client)

        provider = OllamaProvider(ollama_config)
        events = [e async for e in provider.chat_stream(sample_messages)]
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_get_models_returns_list(self, ollama_config, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200, {
            "models": [{"name": "llama3.2", "modified_at": "2024-01-01"}],
        }))
        patch_client(OllamaProvider, monkeypatch, client)

        provider = OllamaProvider(ollama_config)
        models = await provider.get_models()
        assert len(models) == 1
        assert models[0].id == "llama3.2"
        assert models[0].provider == "ollama"

    @pytest.mark.asyncio
    async def test_health_check_success(self, ollama_config, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(200))
        patch_client(OllamaProvider, monkeypatch, client)

        provider = OllamaProvider(ollama_config)
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, ollama_config, monkeypatch):
        client = MockAsyncClient()
        client.add_response(MockResponse(500))
        patch_client(OllamaProvider, monkeypatch, client)

        provider = OllamaProvider(ollama_config)
        assert await provider.health_check() is False

    def test_get_capabilities_returns_default(self):
        caps = OllamaProvider.get_capabilities("any-model")
        assert caps.max_context_tokens == 32768
        assert caps.supports_streaming is True
        assert caps.supports_functions is False
        assert caps.supports_vision is False
        assert caps.cost_per_1k_input == 0.0


# ===================================================================
# ProviderRouter
# ===================================================================

def _make_router_provider(pid: str, chat_return: LLMResponse | None = None, mdl: str = "test-model") -> BaseLLMProvider:
    class _Mock(BaseLLMProvider):
        provider_id = pid
        model = mdl

        async def chat(self, messages: list[LLMMessage]) -> LLMResponse:
            return chat_return or LLMResponse(content=f"from-{pid}")

        async def chat_stream(self, messages: list[LLMMessage]) -> AsyncGenerator[LLMStreamEvent, None]:
            yield LLMStreamEvent(content="stream")

        async def get_models(self) -> list[ModelInfo]:
            return [ModelInfo(id=mdl, provider=pid)]

        async def health_check(self) -> bool:
            return True

    return _Mock(LLMConfig())


class TestProviderRouter:
    def test_register_and_list(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("openai"))
        assert router.list_available() == ["openai"]

    def test_register_multiple_providers(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("p1"))
        router.register_provider(_make_router_provider("p2"))
        assert sorted(router.list_available()) == ["p1", "p2"]

    def test_register_with_capabilities(self):
        router = ProviderRouter()
        provider = _make_router_provider("openai")
        caps = {"gpt-4o-mini": LLMCapabilities(supports_streaming=True, max_context_tokens=128000)}
        router.register_provider(provider, caps)
        assert router._capabilities["openai"]["gpt-4o-mini"].max_context_tokens == 128000

    def test_register_sets_initial_healthy(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("openai"))
        assert router._health_status["openai"] is True

    def test_get_provider_returns_provider(self):
        router = ProviderRouter()
        provider = _make_router_provider("openai")
        router.register_provider(provider)
        assert router.get_provider("openai") is provider

    def test_get_provider_unknown_returns_none(self):
        router = ProviderRouter()
        assert router.get_provider("nonexistent") is None

    def test_select_no_providers_returns_none(self):
        router = ProviderRouter()
        assert router.select(SelectionCriteria()) is None

    def test_select_returns_best_candidate(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("openai"), {
            "gpt-4o-mini": LLMCapabilities(supports_streaming=True, max_context_tokens=128000),
        })
        result = router.select(SelectionCriteria())
        assert isinstance(result, RoutingResult)
        assert result.provider_id == "openai"
        assert result.score > 0

    def test_select_preferred_model_matched(self):
        router = ProviderRouter()
        caps = {
            "gpt-4o": LLMCapabilities(supports_streaming=True, max_context_tokens=128000),
            "gpt-4o-mini": LLMCapabilities(supports_streaming=True, max_context_tokens=128000),
        }
        router.register_provider(_make_router_provider("openai"), caps)
        result = router.select(SelectionCriteria(preferred_models=["gpt-4o"]))
        assert result is not None
        assert result.model == "gpt-4o"

    def test_select_preferred_model_not_in_caps_falls_back_to_default(self):
        router = ProviderRouter()
        caps = {"gpt-4o": LLMCapabilities(supports_streaming=True, max_context_tokens=128000)}
        router.register_provider(_make_router_provider("openai"), caps)
        result = router.select(SelectionCriteria(preferred_models=["nonexistent"]))
        assert result is not None
        # Falls back to default model map entry "gpt-4o-mini" for openai
        assert result.model == "gpt-4o-mini"

    def test_select_uses_default_model_map_when_no_caps(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("openai"))
        result = router.select(SelectionCriteria())
        assert result is not None
        # _default_model_map["openai"] = "gpt-4o-mini" wins over provider.model
        assert result.model == "gpt-4o-mini"

    def test_select_capability_scoring_picks_correct_provider(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("vision_on", mdl="m1"), {
            "m1": LLMCapabilities(supports_vision=True, supports_streaming=True, max_context_tokens=128000),
        })
        router.register_provider(_make_router_provider("vision_off", mdl="m2"), {
            "m2": LLMCapabilities(supports_vision=False, supports_streaming=True, max_context_tokens=128000),
        })
        result = router.select(SelectionCriteria(requires_vision=True))
        assert result is not None
        assert result.provider_id == "vision_on"

    def test_select_streaming_requirement(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("stream_on", mdl="m1"), {
            "m1": LLMCapabilities(supports_streaming=True, max_context_tokens=128000),
        })
        router.register_provider(_make_router_provider("stream_off", mdl="m2"), {
            "m2": LLMCapabilities(supports_streaming=False, max_context_tokens=128000),
        })
        result = router.select(SelectionCriteria(requires_streaming=True))
        assert result is not None
        assert result.provider_id == "stream_on"

    def test_select_functions_requirement(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("func_on", mdl="m1"), {
            "m1": LLMCapabilities(supports_functions=True, max_context_tokens=128000),
        })
        router.register_provider(_make_router_provider("func_off", mdl="m2"), {
            "m2": LLMCapabilities(supports_functions=False, max_context_tokens=128000),
        })
        result = router.select(SelectionCriteria(requires_functions=True))
        assert result is not None
        assert result.provider_id == "func_on"

    def test_select_json_mode_requirement(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("json_on", mdl="m1"), {
            "m1": LLMCapabilities(supports_json_mode=True, max_context_tokens=128000),
        })
        router.register_provider(_make_router_provider("json_off", mdl="m2"), {
            "m2": LLMCapabilities(supports_json_mode=False, max_context_tokens=128000),
        })
        result = router.select(SelectionCriteria(requires_json_mode=True))
        assert result is not None
        assert result.provider_id == "json_on"

    def test_select_required_features_list_grants_bonus(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("full", mdl="m1"), {
            "m1": LLMCapabilities(
                supports_streaming=True, supports_functions=True, supports_vision=True,
                max_context_tokens=128000,
            ),
        })
        router.register_provider(_make_router_provider("partial", mdl="m2"), {
            "m2": LLMCapabilities(
                supports_streaming=True, supports_functions=False, supports_vision=False,
                max_context_tokens=128000,
            ),
        })
        result = router.select(SelectionCriteria(required_features=["streaming", "functions", "vision"]))
        assert result is not None
        assert result.provider_id == "full"

    def test_select_insufficient_context_penalizes(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("small", mdl="m1"), {
            "m1": LLMCapabilities(max_context_tokens=1000),
        })
        router.register_provider(_make_router_provider("large", mdl="m2"), {
            "m2": LLMCapabilities(max_context_tokens=128000),
        })
        result = router.select(SelectionCriteria(min_context_tokens=5000))
        assert result is not None
        assert result.provider_id == "large"

    def test_select_cost_routing_prefers_cheaper(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("cheap", mdl="m1"), {
            "m1": LLMCapabilities(
                supports_streaming=True, max_context_tokens=128000,
                cost_per_1k_input=0.0001, cost_per_1k_output=0.0002,
            ),
        })
        router.register_provider(_make_router_provider("expensive", mdl="m2"), {
            "m2": LLMCapabilities(
                supports_streaming=True, max_context_tokens=128000,
                cost_per_1k_input=10.0, cost_per_1k_output=50.0,
            ),
        })
        result = router.select(SelectionCriteria(estimated_input_tokens=1000, max_cost_per_1k=0.1))
        assert result is not None
        assert result.provider_id == "cheap"

    def test_select_cost_above_max_penalizes(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("p1"), {
            "m1": LLMCapabilities(
                supports_streaming=True, max_context_tokens=128000,
                cost_per_1k_input=1.0, cost_per_1k_output=2.0,
            ),
        })
        result = router.select(SelectionCriteria(estimated_input_tokens=1000, max_cost_per_1k=0.5))
        assert result is not None
        # cost exceeds max -> cost_score = -10, so total should reflect that
        ps = router._score_provider("p1", "m1", SelectionCriteria(estimated_input_tokens=1000, max_cost_per_1k=0.5))
        assert ps.cost_score == -10

    def test_select_latency_scoring(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("fast", mdl="m1"), {
            "m1": LLMCapabilities(supports_streaming=True, max_context_tokens=128000),
        })
        router.register_provider(_make_router_provider("slow", mdl="m2"), {
            "m2": LLMCapabilities(supports_streaming=True, max_context_tokens=128000),
        })
        router._latency_history["fast"] = [50]
        router._latency_history["slow"] = [500]
        result = router.select(SelectionCriteria(max_latency_ms=200))
        assert result is not None
        assert result.provider_id == "fast"

    def test_select_latency_without_history_scores_zero(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("openai", mdl="m1"), {
            "m1": LLMCapabilities(supports_streaming=True, max_context_tokens=128000),
        })
        ps = router._score_provider("openai", "m1", SelectionCriteria())
        assert ps.latency_score == 0.0

    def test_select_health_score_unhealthy(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("unhealthy", mdl="m1"), {
            "m1": LLMCapabilities(supports_streaming=True, max_context_tokens=128000),
        })
        router._health_status["unhealthy"] = False
        ps = router._score_provider("unhealthy", "m1", SelectionCriteria())
        assert ps.health_score == -100.0

    def test_select_failover_picks_healthy_when_best_is_negative(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("bad", mdl="m1"), {
            "m1": LLMCapabilities(max_context_tokens=500),
        })
        router.register_provider(_make_router_provider("good", mdl="m2"), {
            "m2": LLMCapabilities(supports_streaming=True, max_context_tokens=128000),
        })
        router._health_status["bad"] = False
        router._health_status["good"] = True
        # bad: health=-100 + insufficient_context=-50 + caps not found(0) = -150
        # good: health=20 + sufficient_context=25 = 45
        result = router.select(SelectionCriteria(min_context_tokens=1000))
        assert result is not None
        assert result.provider_id == "good"

    def test_select_failover_disabled_keeps_negative_best(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("p1", mdl="m1"), {
            "m1": LLMCapabilities(max_context_tokens=500),
        })
        router.register_provider(_make_router_provider("p2", mdl="m2"), {
            "m2": LLMCapabilities(supports_streaming=True, max_context_tokens=128000),
        })
        router._health_status["p1"] = False
        router._health_status["p2"] = False
        # Both unhealthy, p1 has insufficient context penalty
        # p1: health=-100, insufficient_context=-50, total=-150
        # p2: health=-100, sufficient_context=25, total=-75
        # With failover disabled, best = p2 (higher score -75 > -150) stays even though negative
        result = router.select(SelectionCriteria(min_context_tokens=1000, failover_enabled=False))
        assert result is not None
        assert result.provider_id == "p2"

    def test_select_returns_alternatives(self):
        router = ProviderRouter()
        for pid in ["p1", "p2", "p3", "p4", "p5"]:
            model_name = f"m-{pid}"
            router.register_provider(_make_router_provider(pid, mdl=model_name), {
                model_name: LLMCapabilities(supports_streaming=True, max_context_tokens=128000),
            })
        result = router.select(SelectionCriteria())
        assert result is not None
        assert len(result.alternatives) == 3

    def test_select_no_capabilities_returns_zero_score(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("openai"))
        result = router.select(SelectionCriteria())
        assert result is not None
        # Without capabilities, _score_provider returns all zeros
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_chat_with_failover_success(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("openai", chat_return=LLMResponse(content="OK")), {
            "gpt-4o-mini": LLMCapabilities(supports_streaming=True, max_context_tokens=128000),
        })
        response = await router.chat_with_failover(
            [LLMMessage(role="user", content="Hi")], SelectionCriteria(),
        )
        assert response.content == "OK"

    @pytest.mark.asyncio
    async def test_chat_with_failover_fallback_to_alternative_succeeds(self):
        router = ProviderRouter()

        async def primary_fail(messages):
            raise ConnectionError("primary down")

        primary = _make_router_provider("primary")
        primary.chat = primary_fail  # type: ignore[assignment]
        secondary = _make_router_provider("secondary", chat_return=LLMResponse(content="Fallback OK"))

        router.register_provider(primary, {
            "m1": LLMCapabilities(supports_streaming=True, max_context_tokens=128000),
        })
        router.register_provider(secondary, {
            "m2": LLMCapabilities(supports_streaming=True, max_context_tokens=128000),
        })
        response = await router.chat_with_failover(
            [LLMMessage(role="user", content="Hi")], SelectionCriteria(),
        )
        assert response.content == "Fallback OK"

    @pytest.mark.asyncio
    async def test_chat_with_failover_all_retries_exhausted(self):
        router = ProviderRouter()
        provider = _make_router_provider("openai")

        async def _always_fail(messages):
            raise ValueError("permanent failure")

        provider.chat = _always_fail  # type: ignore[assignment]
        router.register_provider(provider, {
            "gpt-4o-mini": LLMCapabilities(supports_streaming=True, max_context_tokens=128000),
        })
        with pytest.raises(RuntimeError, match="All providers failed"):
            await router.chat_with_failover(
                [LLMMessage(role="user", content="Hi")], SelectionCriteria(),
            )

    @pytest.mark.asyncio
    async def test_chat_with_failover_no_available_provider(self):
        router = ProviderRouter()
        with pytest.raises(RuntimeError, match="No available provider matches the criteria"):
            await router.chat_with_failover(
                [LLMMessage(role="user", content="Hi")], SelectionCriteria(),
            )



    @pytest.mark.asyncio
    async def test_chat_with_failover_records_latency(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("openai", chat_return=LLMResponse(content="Fast")), {
            "gpt-4o-mini": LLMCapabilities(supports_streaming=True, max_context_tokens=128000),
        })
        await router.chat_with_failover(
            [LLMMessage(role="user", content="Hi")], SelectionCriteria(),
        )
        assert "openai" in router._latency_history
        assert len(router._latency_history["openai"]) == 1
        assert router._latency_history["openai"][0] > 0

    @pytest.mark.asyncio
    async def test_chat_with_failover_marks_provider_unhealthy_on_error(self):
        router = ProviderRouter()
        provider = _make_router_provider("openai")

        async def _fail(messages):
            raise ValueError("fail")

        provider.chat = _fail  # type: ignore[assignment]
        router.register_provider(provider, {
            "gpt-4o-mini": LLMCapabilities(supports_streaming=True, max_context_tokens=128000),
        })
        with pytest.raises(RuntimeError):
            await router.chat_with_failover(
                [LLMMessage(role="user", content="Hi")], SelectionCriteria(),
            )
        assert router._health_status["openai"] is False

    def test_latency_history_trimmed_to_100(self):
        router = ProviderRouter()
        for i in range(150):
            router._record_latency("openai", float(i))
        assert len(router._latency_history["openai"]) == 100
        assert router._latency_history["openai"][0] == 50.0
        assert router._latency_history["openai"][-1] == 149.0

    def test_clear_resets_all_state(self):
        router = ProviderRouter()
        router.register_provider(_make_router_provider("p1"))
        router._latency_history["p1"] = [100]
        router._health_status["p1"] = False
        router.clear()
        assert router.list_available() == []
        assert router._latency_history == {}
        assert router._health_status == {}

    def test_list_available_empty_initially(self):
        router = ProviderRouter()
        assert router.list_available() == []

    def test_provider_not_found_returns_none(self):
        router = ProviderRouter()
        assert router.get_provider("missing") is None

