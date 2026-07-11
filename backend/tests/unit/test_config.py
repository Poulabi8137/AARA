from __future__ import annotations

import pytest
from pydantic_core import ValidationError

from app.core.config import GlobalConfig

_VALID_JWT = "a" * 32
_VALID_ENC = "b" * 44


@pytest.fixture(autouse=True)
def _valid_keys_env(monkeypatch):
    """Ensure valid JWT and encryption keys are set for all tests."""
    monkeypatch.setenv("JWT_SECRET", _VALID_JWT)
    monkeypatch.setenv("ENCRYPTION_KEY", _VALID_ENC)


def test_config_defaults():
    config = GlobalConfig()
    assert config.app_name == "aara"
    assert config.app_version == "0.3.0"
    assert config.environment == "development"
    assert config.debug is False
    assert config.log_level == "INFO"
    assert config.job_queue_backend == "local"


def test_config_env_override(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    config = GlobalConfig()
    assert config.environment == "production"
    assert config.log_level == "WARNING"


def test_config_is_production():
    config = GlobalConfig()
    assert config.is_development is True
    assert config.is_production is False


def test_config_project_root():
    config = GlobalConfig()
    assert config.project_root.name == "backend"


def test_config_cors_origins_default():
    config = GlobalConfig()
    assert "http://localhost:3000" in config.cors_origins


def test_config_database_url_default():
    config = GlobalConfig()
    assert "aara_dev.db" in config.database_url


def test_config_insecure_key_warning():
    config = GlobalConfig()
    assert len(config.jwt_secret) >= 32
    assert len(config.encryption_key) >= 32


def test_config_rejects_empty_jwt(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(ValidationError):
        GlobalConfig()


def test_config_rejects_short_jwt(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "short")
    with pytest.raises(ValidationError):
        GlobalConfig()


def test_config_rejects_empty_encryption_key(monkeypatch):
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    with pytest.raises(ValidationError):
        GlobalConfig()
