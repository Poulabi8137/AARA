from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None
    errors: dict[str, Any] | None = None


class MessageResponse(BaseModel):
    message: str
    status: str = "ok"
