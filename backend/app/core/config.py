from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GlobalConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(
        default="sqlite+aiosqlite:///./aara_dev.db",
        validation_alias="DATABASE_URL",
    )
    database_url_sync: str = Field(
        default="sqlite:///./aara_dev.db",
        validation_alias="DATABASE_URL_SYNC",
    )
    database_pool_size: int = Field(default=10, validation_alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, validation_alias="DATABASE_MAX_OVERFLOW")

    qdrant_url: str = Field(default="http://localhost:6333", validation_alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, validation_alias="QDRANT_API_KEY")
    qdrant_prefer_grpc: bool = Field(default=True, validation_alias="QDRANT_PREFER_GRPC")

    redis_url: str = Field(default="redis://localhost:6379", validation_alias="REDIS_URL")
    rate_limit_backend: Literal["memory", "redis"] = Field(
        default="memory", validation_alias="RATE_LIMIT_BACKEND"
    )
    rate_limit_requests_per_minute: int = Field(
        default=60, validation_alias="RATE_LIMIT_REQUESTS_PER_MINUTE", ge=1
    )

    supabase_url: str | None = Field(default=None, validation_alias="SUPABASE_URL")
    supabase_service_key: str | None = Field(default=None, validation_alias="SUPABASE_SERVICE_KEY")

    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    groq_api_key: str | None = Field(default=None, validation_alias="GROQ_API_KEY")
    openrouter_api_key: str | None = Field(default=None, validation_alias="OPENROUTER_API_KEY")

    jwt_secret: str = Field(
        default="",
        validation_alias="JWT_SECRET",
        min_length=32,
    )
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(
        default=60, validation_alias="JWT_EXPIRATION_MINUTES", ge=1
    )
    encryption_key: str = Field(default="", validation_alias="ENCRYPTION_KEY")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"], validation_alias="CORS_ORIGINS"
    )

    frontend_url: str = Field(default="http://localhost:3000", validation_alias="FRONTEND_URL")
    backend_url: str = Field(default="http://localhost:8000", validation_alias="BACKEND_URL")

    smtp_host: str | None = Field(default=None, validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, validation_alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, validation_alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="noreply@aara.local", validation_alias="SMTP_FROM")
    smtp_use_tls: bool = Field(default=True, validation_alias="SMTP_USE_TLS")

    password_reset_token_expire_minutes: int = Field(
        default=30, validation_alias="PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", ge=1
    )

    job_queue_backend: Literal["local", "fastapi", "arq"] = Field(
        default="local", validation_alias="JOB_QUEUE_BACKEND"
    )

    monthly_budget_default: Decimal = Field(
        default=Decimal("5.00"), validation_alias="MONTHLY_BUDGET_DEFAULT"
    )

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", validation_alias="ENV"
    )

    max_upload_size_mb: int = Field(default=50, validation_alias="MAX_UPLOAD_SIZE_MB", ge=1)
    allowed_upload_mime_types: list[str] = Field(
        default=[
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "text/markdown",
        ],
        validation_alias="ALLOWED_UPLOAD_MIME_TYPES",
    )

    app_name: str = "aara"
    app_version: str = "0.3.0"
    debug: bool = Field(default=False, validation_alias="DEBUG")

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        if not v:
            raise ValueError("JWT_SECRET must be set (min 32 characters)")
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        if v == "insecure-jwt-secret-change-me-to-a-secure-value" and info.data.get("environment") == "production":
            raise ValueError("Insecure default JWT_SECRET not allowed in production")
        return v

    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, v: str, info) -> str:
        if not v:
            raise ValueError("ENCRYPTION_KEY must be set")
        if v == "insecure-dev-key" and info.data.get("environment") == "production":
            raise ValueError("Insecure default ENCRYPTION_KEY not allowed in production")
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parent.parent.parent
