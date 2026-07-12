from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings


class SummarizationSettings(BaseSettings):
    default_level: str = "standard"
    max_summary_length: int = 4096
    section_ordering: str = "abstract,background,problem_statement,methodology,experimental_setup,results,discussion,limitations,future_work,conclusion"
    default_grouping: str = "topic"
    citation_mode: str = "inline"
    confidence_threshold: float = 0.3
    literature_review_mode: bool = False
    max_citations_per_section: int = 20
    max_findings: int = 10
    max_gaps: int = 5
    model: str = "gpt-4o"
    temperature: float = 0.3
    max_tokens: int = 2048

    class Config:
        env_prefix = "summarization_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_summarization_settings() -> SummarizationSettings:
    return SummarizationSettings()
