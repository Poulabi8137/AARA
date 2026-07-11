from __future__ import annotations

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True, scope="session")
def _disable_dotenv_for_tests():
    """Prevent GlobalConfig from reading .env during tests so monkeypatch.delenv works correctly."""
    import app.core.config

    original_env_file = app.core.config.GlobalConfig.model_config.get("env_file")
    app.core.config.GlobalConfig.model_config["env_file"] = None
    yield
    app.core.config.GlobalConfig.model_config["env_file"] = original_env_file
