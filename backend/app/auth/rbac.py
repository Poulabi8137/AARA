from __future__ import annotations

from enum import StrEnum

from app.core.exceptions import AuthorizationError


class Role(StrEnum):
    STUDENT = "student"
    RESEARCHER = "researcher"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class Permission(StrEnum):
    WORKSPACE_CREATE = "workspace:create"
    WORKSPACE_READ = "workspace:read"
    WORKSPACE_UPDATE = "workspace:update"
    WORKSPACE_DELETE = "workspace:delete"
    WORKSPACE_MANAGE_MEMBERS = "workspace:manage_members"
    PAPER_CREATE = "paper:create"
    PAPER_READ = "paper:read"
    PAPER_UPDATE = "paper:update"
    PAPER_DELETE = "paper:delete"
    WORKFLOW_CREATE = "workflow:create"
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_CANCEL = "workflow:cancel"
    WORKFLOW_APPROVE = "workflow:approve"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    ADMIN_ACCESS = "admin:access"


class WorkspaceRole(StrEnum):
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.STUDENT: {
        Permission.WORKSPACE_CREATE,
        Permission.WORKSPACE_READ,
        Permission.WORKSPACE_UPDATE,
        Permission.PAPER_CREATE,
        Permission.PAPER_READ,
        Permission.PAPER_UPDATE,
        Permission.PAPER_DELETE,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_CANCEL,
        Permission.USER_READ,
        Permission.USER_UPDATE,
    },
    Role.RESEARCHER: {
        Permission.WORKSPACE_CREATE,
        Permission.WORKSPACE_READ,
        Permission.WORKSPACE_UPDATE,
        Permission.WORKSPACE_DELETE,
        Permission.WORKSPACE_MANAGE_MEMBERS,
        Permission.PAPER_CREATE,
        Permission.PAPER_READ,
        Permission.PAPER_UPDATE,
        Permission.PAPER_DELETE,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_CANCEL,
        Permission.WORKFLOW_APPROVE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
    },
    Role.ADMIN: {
        Permission.WORKSPACE_CREATE,
        Permission.WORKSPACE_READ,
        Permission.WORKSPACE_UPDATE,
        Permission.WORKSPACE_DELETE,
        Permission.WORKSPACE_MANAGE_MEMBERS,
        Permission.PAPER_CREATE,
        Permission.PAPER_READ,
        Permission.PAPER_UPDATE,
        Permission.PAPER_DELETE,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_CANCEL,
        Permission.WORKFLOW_APPROVE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.ADMIN_ACCESS,
    },
    Role.SUPER_ADMIN: set(Permission),
}

WORKSPACE_ROLE_PERMISSIONS: dict[WorkspaceRole, set[Permission]] = {
    WorkspaceRole.VIEWER: {
        Permission.WORKSPACE_READ,
        Permission.PAPER_READ,
        Permission.WORKFLOW_READ,
    },
    WorkspaceRole.EDITOR: {
        Permission.WORKSPACE_READ,
        Permission.WORKSPACE_UPDATE,
        Permission.PAPER_CREATE,
        Permission.PAPER_READ,
        Permission.PAPER_UPDATE,
        Permission.PAPER_DELETE,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_CANCEL,
        Permission.WORKFLOW_APPROVE,
    },
    WorkspaceRole.ADMIN: {
        Permission.WORKSPACE_READ,
        Permission.WORKSPACE_UPDATE,
        Permission.WORKSPACE_DELETE,
        Permission.WORKSPACE_MANAGE_MEMBERS,
        Permission.PAPER_CREATE,
        Permission.PAPER_READ,
        Permission.PAPER_UPDATE,
        Permission.PAPER_DELETE,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_CANCEL,
        Permission.WORKFLOW_APPROVE,
    },
}


class RBACService:
    def user_has_permission(self, user_role: str, permission: Permission) -> bool:
        try:
            role = Role(user_role)
        except ValueError:
            return False
        return permission in ROLE_PERMISSIONS.get(role, set())

    def workspace_member_has_permission(
        self, workspace_role: str, permission: Permission
    ) -> bool:
        try:
            wrole = WorkspaceRole(workspace_role)
        except ValueError:
            return False
        return permission in WORKSPACE_ROLE_PERMISSIONS.get(wrole, set())

    def check_permission(self, user_role: str, permission: Permission) -> None:
        if not self.user_has_permission(user_role, permission):
            raise AuthorizationError(
                f"User with role '{user_role}' lacks permission '{permission.value}'"
            )

    def get_permissions_for_role(self, role_name: str) -> set[Permission]:
        try:
            role = Role(role_name)
        except ValueError:
            return set()
        return ROLE_PERMISSIONS.get(role, set())

    def get_permissions_for_workspace_role(
        self, workspace_role: str
    ) -> set[Permission]:
        try:
            wrole = WorkspaceRole(workspace_role)
        except ValueError:
            return set()
        return WORKSPACE_ROLE_PERMISSIONS.get(wrole, set())
