from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings


class MethodologySettings(BaseSettings):
    confidence_threshold: float = 0.3
    max_methods: int = 5
    max_datasets: int = 10
    max_benchmarks: int = 10
    max_risks: int = 10
    max_practices: int = 8
    evaluation_strictness: str = "standard"
    validation_strictness: str = "standard"
    risk_high_threshold: float = 0.7
    risk_medium_threshold: float = 0.4
    best_practice_mode: str = "standard"
    model: str = "gpt-4o"
    temperature: float = 0.2
    max_tokens: int = 2048
    enable_llm: bool = True
    max_warnings: int = 3

    class Config:
        env_prefix = "methodology_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_methodology_settings() -> MethodologySettings:
    return MethodologySettings()
