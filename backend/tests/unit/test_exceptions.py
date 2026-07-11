from __future__ import annotations

from app.core.exceptions import (
    AARAError,
    ConfigurationError,
    DependencyError,
    ErrorCode,
    FeatureDisabledError,
    KillSwitchActiveError,
    NotFoundError,
    RegistryError,
    ValidationError,
)


class TestErrorCode:
    def test_default_values(self):
        ec = ErrorCode(code="TEST")
        assert ec.code == "TEST"
        assert ec.http_status == 500
        assert ec.message == "Internal server error"


class TestAARAError:
    def test_basic_error(self):
        ec = ErrorCode(code="TEST", http_status=400, message="Test error")
        err = AARAError(ec)
        assert str(err) == "Test error"
        assert err.error_code.code == "TEST"
        assert err.error_code.http_status == 400

    def test_with_original_exception(self):
        original = ValueError("original")
        ec = ErrorCode(code="TEST", message="wrapped")
        err = AARAError(ec, original=original)
        assert err.original is original


class TestConfigurationError:
    def test_without_key(self):
        err = ConfigurationError("bad config")
        assert err.error_code.code == "CONFIG_ERROR"
        assert err.error_code.http_status == 500

    def test_with_key(self):
        err = ConfigurationError("bad config", key="DATABASE_URL")
        assert err.error_code.details.get("key") == "DATABASE_URL"


class TestValidationError:
    def test_without_field(self):
        err = ValidationError("invalid")
        assert err.error_code.http_status == 422

    def test_with_field(self):
        err = ValidationError("invalid", field="email")
        assert err.error_code.details.get("field") == "email"


class TestNotFoundError:
    def test_message_format(self):
        err = NotFoundError("Workspace", "abc-123")
        assert "Workspace" in str(err)
        assert err.error_code.http_status == 404
        assert err.error_code.details["resource_id"] == "abc-123"


class TestRegistryError:
    def test_without_registry(self):
        err = RegistryError("not found")
        assert err.error_code.code == "REGISTRY_ERROR"

    def test_with_registry(self):
        err = RegistryError("not found", registry="AgentRegistry")
        assert err.error_code.details.get("registry") == "AgentRegistry"


class TestDependencyError:
    def test_message(self):
        err = DependencyError("db")
        assert "db" in str(err)
        assert err.error_code.http_status == 500


class TestFeatureDisabledError:
    def test_message(self):
        err = FeatureDisabledError("agent.idea_generation")
        assert "agent.idea_generation" in str(err)
        assert err.error_code.http_status == 403


class TestKillSwitchActiveError:
    def test_message(self):
        err = KillSwitchActiveError("llm_providers")
        assert "llm_providers" in str(err)
        assert err.error_code.http_status == 503
