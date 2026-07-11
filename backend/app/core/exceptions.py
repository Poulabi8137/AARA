from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ErrorCode:
    code: str
    http_status: int = 500
    message: str = "Internal server error"
    details: dict[str, Any] = field(default_factory=dict)


class AARAError(Exception):
    def __init__(self, error_code: ErrorCode, original: Exception | None = None) -> None:
        self.error_code = error_code
        self.original = original
        super().__init__(error_code.message)


class ConfigurationError(AARAError):
    def __init__(self, message: str, key: str | None = None) -> None:
        super().__init__(
            ErrorCode(
                code="CONFIG_ERROR",
                http_status=500,
                message=message,
                details={"key": key} if key else {},
            )
        )


class ValidationError(AARAError):
    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(
            ErrorCode(
                code="VALIDATION_ERROR",
                http_status=422,
                message=message,
                details={"field": field} if field else {},
            )
        )


class NotFoundError(AARAError):
    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(
            ErrorCode(
                code="NOT_FOUND",
                http_status=404,
                message=f"{resource} '{resource_id}' not found",
                details={"resource": resource, "resource_id": resource_id},
            )
        )


class RegistryError(AARAError):
    def __init__(self, message: str, registry: str | None = None) -> None:
        super().__init__(
            ErrorCode(
                code="REGISTRY_ERROR",
                http_status=500,
                message=message,
                details={"registry": registry} if registry else {},
            )
        )


class DependencyError(AARAError):
    def __init__(self, key: str) -> None:
        super().__init__(
            ErrorCode(
                code="DEPENDENCY_ERROR",
                http_status=500,
                message=f"Dependency '{key}' not resolved",
                details={"key": key},
            )
        )


class FeatureDisabledError(AARAError):
    def __init__(self, feature: str) -> None:
        super().__init__(
            ErrorCode(
                code="FEATURE_DISABLED",
                http_status=403,
                message=f"Feature '{feature}' is disabled",
                details={"feature": feature},
            )
        )


class KillSwitchActiveError(AARAError):
    def __init__(self, switch: str) -> None:
        super().__init__(
            ErrorCode(
                code="KILL_SWITCH_ACTIVE",
                http_status=503,
                message=f"Kill switch '{switch}' is active",
                details={"switch": switch},
            )
        )


class AuthorizationError(AARAError):
    def __init__(self, message: str) -> None:
        super().__init__(
            ErrorCode(
                code="AUTHORIZATION_ERROR",
                http_status=403,
                message=message,
            )
        )


class AuthenticationError(AARAError):
    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(
            ErrorCode(
                code="AUTHENTICATION_ERROR",
                http_status=401,
                message=message,
            )
        )
