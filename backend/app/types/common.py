from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

T = TypeVar("T")


@dataclass
class PaginationParams:
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


@dataclass
class PaginatedResponse(Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(cls, items: list[T], total: int, params: PaginationParams) -> PaginatedResponse[T]:
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=max(1, -(-total // params.page_size)),
        )


@dataclass
class ErrorResponse:
    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


@dataclass
class HealthStatus:
    status: str = "ok"
    version: str = "0.1.0"
    environment: str = "development"
    timestamp: datetime | None = None
    checks: dict[str, bool] | None = None


@dataclass
class AuditEntry:
    actor_id: UUID | None
    action: str
    resource_type: str
    resource_id: str
    details: dict[str, Any] | None = None
    timestamp: datetime | None = None
