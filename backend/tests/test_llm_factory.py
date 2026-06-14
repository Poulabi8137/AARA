from __future__ import annotations

import pytest
from typing import Any

from app.llm.factory import get_llm_provider, validate_provider_config, ProviderInitError
from app.llm.provider import LLMProvider, ProviderConfig
from app.core.config import Settings


# ── Helpers ──────────────────────────────────────────────

def _make_settings(**overrides: Any) -> Settings:
    defaults: dict[str, Any] = {
        "llm_provider": "mock",
        "llm_model": "gpt-4o",
        "llm_temperature": 0.0,
        "llm_max_tokens": 4096,
        "openai_api_key": "",
        "gemini_api_key": "",
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


# ── Factory Tests ────────────────────────────────────────

class TestFactory:
    def test_get_mock_provider(self) -> None:
        settings = _make_settings(llm_provider="mock")
        provider = get_llm_provider(settings)
        assert isinstance(provider, LLMProvider)
        assert provider.config.model == "gpt-4o"
        assert provider.config.temperature == 0.0

    def test_get_openai_provider_fails_without_key(self) -> None:
        settings = _make_settings(llm_provider="openai", openai_api_key="")
        with pytest.raises(ProviderInitError, match="OPENAI_API_KEY"):
            get_llm_provider(settings)

    def test_get_openai_provider_with_key(self) -> None:
        settings = _make_settings(llm_provider="openai", openai_api_key="sk-test123")
        provider = get_llm_provider(settings)
        assert isinstance(provider, LLMProvider)
        assert provider.config.model == "gpt-4o"
        assert provider.config.temperature == 0.0

    def test_get_gemini_provider_fails_without_key(self) -> None:
        settings = _make_settings(llm_provider="gemini", gemini_api_key="")
        with pytest.raises(ProviderInitError, match="GEMINI_API_KEY"):
            get_llm_provider(settings)

    def test_get_gemini_provider_with_key(self) -> None:
        settings = _make_settings(llm_provider="gemini", gemini_api_key="ai-test123")
        provider = get_llm_provider(settings)
        assert isinstance(provider, LLMProvider)
        assert provider.config.model == "gpt-4o"

    def test_unknown_provider_raises(self) -> None:
        settings = _make_settings(llm_provider="anthropic")
        with pytest.raises(ProviderInitError, match="Unknown LLM provider"):
            get_llm_provider(settings)

    def test_provider_config_injected(self) -> None:
        settings = _make_settings(
            llm_provider="mock",
            llm_model="custom-model",
            llm_temperature=0.7,
            llm_max_tokens=2048,
        )
        provider = get_llm_provider(settings)
        assert provider.config.model == "custom-model"
        assert provider.config.temperature == 0.7
        assert provider.config.max_tokens == 2048

    def test_mock_provider_generates(self) -> None:
        import asyncio
        settings = _make_settings(llm_provider="mock")
        provider = get_llm_provider(settings)
        response = asyncio.run(provider.generate("test prompt"))
        assert response.content
        assert response.model == "mock"
        assert response.usage is not None

    def test_mock_provider_counts_tokens(self) -> None:
        import asyncio
        settings = _make_settings(llm_provider="mock")
        provider = get_llm_provider(settings)
        count = asyncio.run(provider.count_tokens("hello world"))
        assert count == 2


# ── Startup Validation Tests ────────────────────────────

class TestStartupValidation:
    def test_valid_mock_provider(self) -> None:
        settings = _make_settings(llm_provider="mock")
        errors = validate_provider_config(settings)
        assert errors == []

    def test_valid_openai_provider(self) -> None:
        settings = _make_settings(llm_provider="openai", openai_api_key="sk-test")
        errors = validate_provider_config(settings)
        assert errors == []

    def test_valid_gemini_provider(self) -> None:
        settings = _make_settings(llm_provider="gemini", gemini_api_key="ai-test")
        errors = validate_provider_config(settings)
        assert errors == []

    def test_unknown_provider(self) -> None:
        settings = _make_settings(llm_provider="anthropic")
        errors = validate_provider_config(settings)
        assert len(errors) >= 1
        assert any("anthropic" in e for e in errors)

    def test_missing_openai_key(self) -> None:
        settings = _make_settings(llm_provider="openai", openai_api_key="")
        errors = validate_provider_config(settings)
        assert any("OPENAI_API_KEY" in e for e in errors)

    def test_missing_gemini_key(self) -> None:
        settings = _make_settings(llm_provider="gemini", gemini_api_key="")
        errors = validate_provider_config(settings)
        assert any("GEMINI_API_KEY" in e for e in errors)

    def test_empty_model(self) -> None:
        settings = _make_settings(llm_provider="mock", llm_model="")
        errors = validate_provider_config(settings)
        assert any("LLM_MODEL" in e for e in errors)

    def test_invalid_temperature(self) -> None:
        settings = _make_settings(llm_provider="mock", llm_temperature=3.0)
        errors = validate_provider_config(settings)
        assert any("TEMPERATURE" in e.upper() for e in errors)

    def test_multiple_errors(self) -> None:
        settings = _make_settings(
            llm_provider="openai",
            openai_api_key="",
            llm_model="",
            llm_temperature=-1.0,
        )
        errors = validate_provider_config(settings)
        assert len(errors) >= 2


# ── Graph Node Integration Tests ─────────────────────────

class TestGraphInjection:
    @pytest.mark.asyncio
    async def test_planner_node_uses_settings_provider(self) -> None:
        from app.graphs.nodes import planner_node
        from app.agents.state import make_initial_state
        state = make_initial_state(query="test")
        result = await planner_node(state)
        assert result["status"] == "planner_complete"
        assert result["planner_output"] is not None

    @pytest.mark.asyncio
    async def test_retrieval_node_uses_settings_provider(self) -> None:
        from app.graphs.nodes import retrieval_node
        from app.agents.state import make_initial_state
        state = make_initial_state(query="test")
        state["planner_output"] = '{"subtopics": ["s1"], "search_queries": ["q1"]}'
        result = await retrieval_node(state)
        assert result["status"] == "retrieval_complete"

    @pytest.mark.asyncio
    async def test_summarizer_node_uses_settings_provider(self) -> None:
        from app.graphs.nodes import summarizer_node
        from app.agents.state import make_initial_state
        state = make_initial_state(query="test")
        state["retrieved_documents"] = [
            {"subtopic": "s1", "evidence": [{"content": "doc1", "chunk_id": "c1"}], "sources": ["src"], "confidence_score": 80.0, "coverage": True},
        ]
        result = await summarizer_node(state)
        assert result["status"] == "summarizer_complete"
        assert len(result["summaries"]) == 1

    @pytest.mark.asyncio
    async def test_gap_detection_node_uses_settings_provider(self) -> None:
        from app.graphs.nodes import gap_detection_node
        from app.agents.state import make_initial_state
        state = make_initial_state(query="test")
        state["planner_output"] = '{"subtopics": ["s1", "s2"], "research_questions": ["q1"], "search_queries": ["q1"], "priority_areas": ["p1"], "risk_areas": ["r1"]}'
        state["summaries"] = [{"subtopic": "s1", "executive_summary": "summary", "key_findings": ["f1"], "citation_count": 0, "source_count": 0, "confidence_score": 50, "contradictions": [], "supporting_evidence": [], "important_statistics": [], "consensus_points": [], "citations": []}]
        result = await gap_detection_node(state)
        assert result["status"] == "gap_detection_complete"
        assert len(result["research_gaps"]) > 0

    @pytest.mark.asyncio
    async def test_report_generator_node_uses_settings_provider(self) -> None:
        from app.graphs.nodes import report_generator_node
        from app.agents.state import make_initial_state
        state = make_initial_state(query="test")
        state["planner_output"] = '{"subtopics": ["s1"]}'
        state["summaries"] = [{"subtopic": "s1", "executive_summary": "summary text here", "key_findings": ["f1"], "citation_count": 1, "source_count": 1, "confidence_score": 75, "contradictions": [], "citations": [{"claim": "c1", "source": "arxiv", "supporting_chunk_ids": ["c1"]}], "supporting_evidence": ["evidence"], "important_statistics": ["73%"], "consensus_points": ["cp1"]}]
        state["research_gaps"] = [{"gap_id": "g1", "gap_type": "LOW_EVIDENCE", "severity": "high", "description": "gap", "confidence": 75}]
        result = await report_generator_node(state)
        assert result["status"] == "report_generation_complete"
        assert result["generated_report"] is not None
        assert len(result["generated_report"]) > 100


# ── ProviderInitError Tests ─────────────────────────────

class TestProviderInitError:
    def test_is_runtime_error(self) -> None:
        assert issubclass(ProviderInitError, RuntimeError)

    def test_can_be_raised(self) -> None:
        with pytest.raises(ProviderInitError, match="test error"):
            raise ProviderInitError("test error")


# ── ProviderConfig Tests ────────────────────────────────

class TestProviderConfig:
    def test_defaults(self) -> None:
        cfg = ProviderConfig()
        assert cfg.model == "gpt-4o"
        assert cfg.temperature == 0.0
        assert cfg.max_tokens == 4096

    def test_custom_values(self) -> None:
        cfg = ProviderConfig(model="gemini-2.0-flash", temperature=0.5, max_tokens=8192)
        assert cfg.model == "gemini-2.0-flash"
        assert cfg.temperature == 0.5
        assert cfg.max_tokens == 8192
