from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AgentWatch API"
    app_version: str = "0.1.0"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://agentwatch:agentwatch@localhost:5432/agentwatch"
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 20

    secret_key: str = ""
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # Security
    token_version: int = 1
    password_min_length: int = 8
    password_max_length: int = 128
    max_login_attempts: int = 5
    login_lockout_minutes: int = 15
    reset_token_expire_hours: int = 1
    require_email_verification: bool = False
    cors_allow_credentials: bool = True

    max_upload_size: int = 10 * 1024 * 1024  # 10 MB

    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    log_level: str = "INFO"
    log_format: str = "json"

    vectorstore_persist_dir: str = "./chroma_data"
    vectorstore_collection_count: int = 5
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    llm_provider: str = "mock"
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096
    openai_api_key: str = ""
    gemini_api_key: str = ""

    redis_url: str = "memory"
    redis_pool_size: int = 10
    redis_max_retries: int = 3
    redis_socket_timeout: int = 5
    redis_socket_connect_timeout: int = 5
    redis_health_check_interval: int = 30
    default_cache_ttl: int = 300

    workflow_max_retries: int = 3
    workflow_node_timeout: int = 120
    require_human_approval: bool = False

    # Observability
    env: str = "development"
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1
    sentry_profiles_sample_rate: float = 0.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
