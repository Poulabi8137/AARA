from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.repositories.base import BaseRepository
from app.repositories.paper_repository import PaperRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession)
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


class TestBaseRepository:
    @pytest.fixture
    def repo(self):
        return BaseRepository(User)

    async def test_create_and_get(self, db, repo):
        user = await repo.create(db, id="u1", email="test@test.com")
        assert user.id == "u1"

        fetched = await repo.get(db, "u1")
        assert fetched.email == "test@test.com"

    async def test_get_not_found(self, db, repo):
        with pytest.raises(NotFoundError):
            await repo.get(db, "nonexistent")

    async def test_create_and_get_many(self, db, repo):
        await repo.create(db, id="u1", email="a@b.com")
        await repo.create(db, id="u2", email="c@d.com")
        users = await repo.get_many(db)
        assert len(users) == 2

    async def test_update(self, db, repo):
        await repo.create(db, id="u1", email="old@test.com")
        updated = await repo.update(db, "u1", email="new@test.com")
        assert updated.email == "new@test.com"

    async def test_delete(self, db, repo):
        await repo.create(db, id="u1", email="test@test.com")
        await repo.delete(db, "u1")
        with pytest.raises(NotFoundError):
            await repo.get(db, "u1")

    async def test_exists(self, db, repo):
        await repo.create(db, id="u1", email="test@test.com")
        assert await repo.exists(db, "u1") is True
        assert await repo.exists(db, "nonexistent") is False

    async def test_count(self, db, repo):
        await repo.create(db, id="u1", email="a@b.com")
        await repo.create(db, id="u2", email="c@d.com")
        count = await repo.count(db)
        assert count == 2


class TestUserRepository:
    @pytest.fixture
    def repo(self):
        return UserRepository()

    async def test_get_by_email_found(self, db, repo):
        await repo.create(db, id="u1", email="test@test.com")
        user = await repo.get_by_email(db, "test@test.com")
        assert user is not None
        assert user.id == "u1"

    async def test_get_by_email_not_found(self, db, repo):
        user = await repo.get_by_email(db, "nonexistent@test.com")
        assert user is None


class TestWorkspaceRepository:
    @pytest.fixture
    def repo(self):
        return WorkspaceRepository()

    async def test_get_by_owner(self, db, repo):
        await repo.create(db, id="w1", owner_id="u1", name="WS1")
        await repo.create(db, id="w2", owner_id="u1", name="WS2")
        workspaces = await repo.get_by_owner(db, "u1")
        assert len(workspaces) == 2

    async def test_get_for_user_as_owner(self, db, repo):
        await repo.create(db, id="w1", owner_id="u1", name="WS1")
        workspaces = await repo.get_for_user(db, "u1")
        assert len(workspaces) == 1

    async def test_add_and_remove_member(self, db, repo):
        await repo.create(db, id="w1", owner_id="u1", name="WS1")
        member = await repo.add_member(db, "w1", "u2", role="editor")
        assert member.role == "editor"

        role = await repo.get_member_role(db, "w1", "u2")
        assert role == "editor"

        await repo.remove_member(db, "w1", "u2")
        role = await repo.get_member_role(db, "w1", "u2")
        assert role is None

    async def test_get_member_count(self, db, repo):
        await repo.create(db, id="w1", owner_id="u1", name="WS1")
        await repo.add_member(db, "w1", "u2")
        await repo.add_member(db, "w1", "u3")
        count = await repo.get_member_count(db, "w1")
        assert count == 2


class TestPaperRepository:
    @pytest.fixture
    def repo(self):
        return PaperRepository()

    async def test_find_by_content_hash_scoped_to_workspace(self, db, repo):
        await repo.create(
            db, id="p1", workspace_id="ws-1", title="Paper A", source="upload",
            content_hash="hash-1",
        )

        found = await repo.find_by_content_hash(db, "hash-1", "ws-1")
        assert found is not None
        assert found.id == "p1"

        # A user in a different workspace must not be able to discover the
        # paper by guessing/colliding on the same content hash.
        not_found = await repo.find_by_content_hash(db, "hash-1", "ws-2")
        assert not_found is None

    async def test_find_by_doi_scoped_to_workspace(self, db, repo):
        await repo.create(
            db, id="p1", workspace_id="ws-1", title="Paper A", source="upload",
            doi="10.1234/test",
        )

        found = await repo.find_by_doi(db, "10.1234/test", "ws-1")
        assert found is not None
        assert found.id == "p1"

        not_found = await repo.find_by_doi(db, "10.1234/test", "ws-2")
        assert not_found is None

    async def test_get_by_workspace_ids_bulk_lookup(self, db, repo):
        await repo.create(db, id="p1", workspace_id="ws-1", title="Paper A", source="upload")
        await repo.create(db, id="p2", workspace_id="ws-2", title="Paper B", source="upload")
        await repo.create(db, id="p3", workspace_id="ws-3", title="Paper C", source="upload")

        found = await repo.get_by_workspace_ids(db, ["ws-1", "ws-2"])
        assert {p.id for p in found} == {"p1", "p2"}

    async def test_get_by_workspace_ids_empty_input(self, db, repo):
        assert await repo.get_by_workspace_ids(db, []) == []


class TestProjectRepository:
    @pytest.fixture
    def repo(self):
        return ProjectRepository()

    async def test_get_by_workspace_ids_bulk_lookup(self, db, repo):
        await repo.create(db, id="proj-1", workspace_id="ws-1", name="P1")
        await repo.create(db, id="proj-2", workspace_id="ws-2", name="P2")
        await repo.create(db, id="proj-3", workspace_id="ws-3", name="P3")

        found = await repo.get_by_workspace_ids(db, ["ws-1", "ws-2"])
        assert {p.id for p in found} == {"proj-1", "proj-2"}

    async def test_get_by_workspace_ids_empty_input(self, db, repo):
        assert await repo.get_by_workspace_ids(db, []) == []


class TestSessionRepository:
    @pytest.fixture
    def repo(self):
        return SessionRepository()

    async def test_get_by_project_ids_bulk_lookup(self, db, repo):
        await repo.create(db, id="s1", project_id="proj-1", status="pending")
        await repo.create(db, id="s2", project_id="proj-2", status="pending")
        await repo.create(db, id="s3", project_id="proj-3", status="pending")

        found = await repo.get_by_project_ids(db, ["proj-1", "proj-2"])
        assert {s.id for s in found} == {"s1", "s2"}

    async def test_get_by_project_ids_empty_input(self, db, repo):
        assert await repo.get_by_project_ids(db, []) == []

    async def test_get_recent_by_workspace_ids_bulk_lookup(self, db, repo):
        project_repo = ProjectRepository()
        await project_repo.create(db, id="proj-1", workspace_id="ws-1", name="P1")
        await project_repo.create(db, id="proj-2", workspace_id="ws-2", name="P2")
        await repo.create(db, id="s1", project_id="proj-1", status="pending")
        await repo.create(db, id="s2", project_id="proj-2", status="pending")

        found = await repo.get_recent_by_workspace_ids(db, ["ws-1", "ws-2"])
        assert {s.id for s in found} == {"s1", "s2"}

    async def test_get_recent_by_workspace_ids_empty_input(self, db, repo):
        assert await repo.get_recent_by_workspace_ids(db, []) == []
