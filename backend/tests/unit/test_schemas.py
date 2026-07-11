from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import (
    EmailVerificationRequest,
    ErrorResponse,
    LoginRequest,
    MessageResponse,
    PaginatedResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
)


class TestAuthSchemas:
    def test_login_request_valid(self):
        r = LoginRequest(email="user@test.com", password="password123")
        assert r.email == "user@test.com"

    def test_login_request_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="not-email", password="password123")

    def test_register_request_valid(self):
        r = RegisterRequest(email="user@test.com", password="Password123!", display_name="User")
        assert r.display_name == "User"

    def test_register_request_weak_password_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@test.com", password="password123", display_name="User")

    def test_refresh_token_request(self):
        r = RefreshTokenRequest(refresh_token="tok")
        assert r.refresh_token == "tok"

    def test_token_response(self):
        r = TokenResponse(access_token="at", refresh_token="rt", expires_in=3600)
        assert r.token_type == "bearer"

    def test_user_response_from_attrs(self):
        r = UserResponse.model_validate({"id": "1", "email": "a@b.com"})
        assert r.email == "a@b.com"
        assert r.role == "student"

    def test_password_reset_request(self):
        r = PasswordResetRequest(email="a@b.com")
        assert r.email == "a@b.com"

    def test_password_reset_confirm(self):
        r = PasswordResetConfirmRequest(token="t", new_password="NewPass123!")
        assert r.token == "t"

    def test_password_reset_confirm_weak_password_rejected(self):
        with pytest.raises(ValidationError):
            PasswordResetConfirmRequest(token="t", new_password="newpass123")

    def test_email_verification_request(self):
        r = EmailVerificationRequest(token="t")
        assert r.token == "t"


class TestWorkspaceSchemas:
    def test_workspace_create_valid(self):
        w = WorkspaceCreate(name="My Workspace", description="desc")
        assert w.name == "My Workspace"
        assert w.description == "desc"

    def test_workspace_create_minimal(self):
        w = WorkspaceCreate(name="Test")
        assert w.description is None

    def test_workspace_update(self):
        w = WorkspaceUpdate(name="New", status="active")
        assert w.name == "New"

    def test_workspace_response_from_attrs(self):
        w = WorkspaceResponse.model_validate({
            "id": "w1", "name": "Test", "owner_id": "u1"
        })
        assert w.name == "Test"
        assert w.member_count == 0


class TestCommonSchemas:
    def test_paginated_response(self):
        r = PaginatedResponse(items=[1, 2, 3], total=3, page=1, page_size=10, total_pages=1)
        assert len(r.items) == 3

    def test_paginated_response_empty(self):
        r = PaginatedResponse(items=[], total=0, page=1, page_size=10, total_pages=0)
        assert r.total == 0

    def test_error_response(self):
        r = ErrorResponse(detail="Not found")
        assert r.detail == "Not found"

    def test_error_response_with_code(self):
        r = ErrorResponse(detail="err", error_code="NOT_FOUND")
        assert r.error_code == "NOT_FOUND"

    def test_message_response(self):
        r = MessageResponse(message="ok")
        assert r.status == "ok"
