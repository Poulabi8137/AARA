from __future__ import annotations

from app.models import (
    Organization,
    OrganizationMember,
    User,
    UserPreferences,
    Workspace,
    WorkspaceMember,
    WorkspaceSettings,
)


class TestUserModel:
    def test_defaults(self):
        u = User(id="u1", email="test@test.com", role="student", is_active=True)
        assert u.email == "test@test.com"
        assert u.role == "student"
        assert u.is_active is True

    def test_tablename(self):
        assert User.__tablename__ == "users"


class TestWorkspaceModel:
    def test_defaults(self):
        w = Workspace(id="w1", owner_id="u1", name="test", status="active")
        assert w.name == "test"
        assert w.status == "active"

    def test_tablename(self):
        assert Workspace.__tablename__ == "workspaces"


class TestWorkspaceMemberModel:
    def test_creation(self):
        m = WorkspaceMember(workspace_id="w1", user_id="u1", role="editor")
        assert m.role == "editor"

    def test_composite_pk(self):
        assert WorkspaceMember.__tablename__ == "workspace_members"


class TestWorkspaceSettingsModel:
    def test_defaults(self):
        s = WorkspaceSettings(workspace_id="w1", preferred_llm_provider="openai",
                            preferred_llm_model="gpt-4o-mini", max_papers_per_search=50)
        assert s.preferred_llm_provider == "openai"
        assert s.preferred_llm_model == "gpt-4o-mini"
        assert s.max_papers_per_search == 50

    def test_tablename(self):
        assert WorkspaceSettings.__tablename__ == "workspace_settings"


class TestOrganizationModel:
    def test_creation(self):
        o = Organization(id="o1", name="Test Org", owner_id="u1")
        assert o.name == "Test Org"

    def test_tablename(self):
        assert Organization.__tablename__ == "organizations"


class TestOrganizationMemberModel:
    def test_defaults(self):
        m = OrganizationMember(organization_id="o1", user_id="u1", role="member")
        assert m.role == "member"

    def test_tablename(self):
        assert OrganizationMember.__tablename__ == "organization_members"


class TestUserPreferencesModel:
    def test_defaults(self):
        p = UserPreferences(user_id="u1", theme="system", notifications_enabled=True)
        assert p.theme == "system"
        assert p.notifications_enabled is True

    def test_tablename(self):
        assert UserPreferences.__tablename__ == "user_preferences"


class TestModelsImports:
    def test_all_imports(self):
        from app.models import (
            Organization,
            OrganizationMember,
            User,
            UserPreferences,
            Workspace,
            WorkspaceMember,
            WorkspaceSettings,
        )
        assert User is not None
        assert Workspace is not None
        assert WorkspaceMember is not None
        assert WorkspaceSettings is not None
        assert Organization is not None
        assert OrganizationMember is not None
        assert UserPreferences is not None
