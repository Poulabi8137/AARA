from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings


class PlannerSettings(BaseSettings):
    max_planning_depth: int = 5
    max_task_count: int = 20
    dependency_validation: bool = True
    parallel_planning: bool = True
    ambiguity_threshold: float = 0.4
    confidence_threshold: float = 0.3
    strategy_selection: str = "auto"
    default_strategy: str = "general"
    enable_memory_lookup: bool = True
    version: str = "1.0"

    class Config:
        env_prefix = "planner_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_planner_settings() -> PlannerSettings:
    return PlannerSettings()
