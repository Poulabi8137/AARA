from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings


class ExperimentSettings(BaseSettings):
    hypothesis_confidence_threshold: float = 0.3
    experiment_complexity: str = "moderate"
    max_experiment_phases: int = 6
    max_experiment_steps: int = 30
    baseline_limits: int = 5
    benchmark_limits: int = 5
    evaluation_strictness: str = "standard"
    resource_estimation_mode: str = "auto"
    validation_strictness: str = "standard"
    max_hypotheses: int = 5
    max_variables: int = 15
    max_risks: int = 10
    temperature: float = 0.2
    max_tokens: int = 2048
    enable_llm: bool = True
    model: str = "gpt-4o"
    max_warnings: int = 3

    class Config:
        env_prefix = "experiment_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_experiment_settings() -> ExperimentSettings:
    return ExperimentSettings()
