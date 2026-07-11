from __future__ import annotations

import pytest

from app.auth.jwt_handler import JWTHandler
from app.auth.rbac import Permission, RBACService
from app.core.exceptions import AuthorizationError, ConfigurationError


class TestJWTHandler:
    @pytest.fixture
    def handler(self):
        return JWTHandler(
            secret="test-secret-key-32-chars-minimum!!",
            algorithm="HS256",
            access_token_ttl=3600,
            refresh_token_ttl=2592000,
        )

    async def test_create_and_verify_access_token(self, handler):
        token = await handler.create_access_token(subject="user-123")
        payload = await handler.verify_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    async def test_create_and_verify_refresh_token(self, handler):
        token = await handler.create_refresh_token(subject="user-123")
        payload = await handler.verify_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"

    async def test_refresh_access_token(self, handler):
        refresh = await handler.create_refresh_token(subject="user-123")
        new_token = await handler.refresh_access_token(refresh)
        payload = await handler.verify_token(new_token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    async def test_expired_token_raises(self, handler):
        handler._access_token_ttl = -1
        token = await handler.create_access_token(subject="user-123")
        with pytest.raises(ConfigurationError):
            await handler.verify_token(token)

    async def test_no_secret_raises(self):
        h = JWTHandler()
        with pytest.raises(ConfigurationError):
            await h.create_access_token(subject="user-123")

    async def test_hash_and_verify_password(self, handler):
        hashed = await handler.hash_password("mypassword")
        assert await handler.verify_password("mypassword", hashed)
        assert not await handler.verify_password("wrong", hashed)


class TestRBAC:
    @pytest.fixture
    def rbac(self):
        return RBACService()

    def test_student_has_basic_permissions(self, rbac):
        assert rbac.user_has_permission("student", Permission.WORKSPACE_CREATE)
        assert not rbac.user_has_permission("student", Permission.ADMIN_ACCESS)

    def test_admin_has_admin_access(self, rbac):
        assert rbac.user_has_permission("admin", Permission.ADMIN_ACCESS)

    def test_super_admin_has_all(self, rbac):
        assert rbac.user_has_permission("super_admin", Permission.ADMIN_ACCESS)
        assert rbac.user_has_permission("super_admin", Permission.WORKSPACE_CREATE)

    def test_unknown_role_has_no_permissions(self, rbac):
        assert not rbac.user_has_permission("unknown", Permission.WORKSPACE_CREATE)

    def test_workspace_viewer_permissions(self, rbac):
        assert rbac.workspace_member_has_permission("viewer", Permission.WORKSPACE_READ)
        assert not rbac.workspace_member_has_permission("viewer", Permission.WORKSPACE_UPDATE)

    def test_workspace_admin_has_all_workspace_perms(self, rbac):
        assert rbac.workspace_member_has_permission("admin", Permission.WORKSPACE_DELETE)
        assert rbac.workspace_member_has_permission("admin", Permission.WORKSPACE_MANAGE_MEMBERS)

    def test_check_permission_passes(self, rbac):
        rbac.check_permission("admin", Permission.WORKSPACE_CREATE)

    def test_check_permission_raises(self, rbac):
        with pytest.raises(AuthorizationError):
            rbac.check_permission("student", Permission.ADMIN_ACCESS)

    def test_get_permissions_for_role(self, rbac):
        perms = rbac.get_permissions_for_role("student")
        assert Permission.WORKSPACE_CREATE in perms
        assert Permission.ADMIN_ACCESS not in perms

    def test_get_permissions_for_unknown_role(self, rbac):
        assert rbac.get_permissions_for_role("nonexistent") == set()

    def test_get_workspace_role_permissions(self, rbac):
        perms = rbac.get_permissions_for_workspace_role("viewer")
        assert Permission.WORKSPACE_READ in perms
        assert Permission.WORKSPACE_DELETE not in perms
