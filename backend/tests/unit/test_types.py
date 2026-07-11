from __future__ import annotations

from app.types.common import (
    AuditEntry,
    ErrorResponse,
    HealthStatus,
    PaginatedResponse,
    PaginationParams,
)


class TestPaginationParams:
    def test_defaults(self):
        p = PaginationParams()
        assert p.page == 1
        assert p.page_size == 20

    def test_offset(self):
        p = PaginationParams(page=3, page_size=10)
        assert p.offset == 20

    def test_limit(self):
        p = PaginationParams(page_size=50)
        assert p.limit == 50


class TestPaginatedResponse:
    def test_create(self):
        params = PaginationParams(page=1, page_size=10)
        response = PaginatedResponse.create(items=["a", "b"], total=25, params=params)
        assert len(response.items) == 2
        assert response.total == 25
        assert response.page == 1
        assert response.page_size == 10
        assert response.total_pages == 3

    def test_empty(self):
        params = PaginationParams(page=1, page_size=10)
        response = PaginatedResponse.create(items=[], total=0, params=params)
        assert response.total_pages == 1


class TestErrorResponse:
    def test_minimal(self):
        err = ErrorResponse(code="NOT_FOUND", message="Resource not found")
        assert err.code == "NOT_FOUND"
        assert err.details is None

    def test_with_details(self):
        err = ErrorResponse(code="VALIDATION_ERROR", message="Invalid", details={"field": "email"})
        assert err.details["field"] == "email"


class TestHealthStatus:
    def test_defaults(self):
        h = HealthStatus()
        assert h.status == "ok"
        assert h.version == "0.1.0"


class TestAuditEntry:
    def test_minimal(self):
        entry = AuditEntry(
            actor_id=None, action="create", resource_type="workspace", resource_id="1"
        )
        assert entry.action == "create"
