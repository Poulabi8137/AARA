from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings


class AnalysisSettings(BaseSettings):
    contradiction_threshold: float = 0.4
    consensus_threshold: float = 0.6
    trend_window_years: int = 3
    confidence_weights: str = "0.25,0.20,0.25,0.15,0.15"
    max_recommendations: int = 10
    max_contradictions: int = 10
    max_consensus: int = 15
    max_trends: int = 8
    max_limitations: int = 10
    max_relationships: int = 50
    relationship_confidence: float = 0.5
    model: str = "gpt-4o"
    temperature: float = 0.2
    max_tokens: int = 2048
    enable_llm_analysis: bool = True

    class Config:
        env_prefix = "analysis_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_analysis_settings() -> AnalysisSettings:
    return AnalysisSettings()
