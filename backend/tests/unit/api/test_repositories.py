from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.models.workspace import Workspace
from app.repositories.citation_repository import CitationRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.paper_repository import PaperRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.session_repository import SessionRepository

WS_ID: str = ""


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession)
    session = session_factory()
    user = User(id=str(uuid.uuid4()), email="test@example.com")
    session.add(user)
    ws = Workspace(id=str(uuid.uuid4()), owner_id=user.id, name="Test WS")
    session.add(ws)
    await session.flush()
    global WS_ID
    WS_ID = ws.id
    yield session
    await session.close()
    await engine.dispose()


class TestProjectRepository:
    @pytest.mark.asyncio
    async def test_create(self, db: AsyncSession):
        repo = ProjectRepository()
        p = await repo.create(db, workspace_id=WS_ID, name="Test Project")
        assert p.id is not None
        assert p.name == "Test Project"
        assert p.status == "active"

    @pytest.mark.asyncio
    async def test_get(self, db: AsyncSession):
        repo = ProjectRepository()
        p = await repo.create(db, workspace_id=WS_ID, name="Get Me")
        fetched = await repo.get(db, p.id)
        assert fetched.id == p.id
        assert fetched.name == "Get Me"

    @pytest.mark.asyncio
    async def test_get_not_found(self, db: AsyncSession):
        repo = ProjectRepository()
        with pytest.raises(NotFoundError):
            await repo.get(db, "nonexistent")

    @pytest.mark.asyncio
    async def test_get_by_workspace(self, db: AsyncSession):
        repo = ProjectRepository()
        await repo.create(db, workspace_id=WS_ID, name="P1")
        await repo.create(db, workspace_id=WS_ID, name="P2")
        projects = await repo.get_by_workspace(db, WS_ID)
        assert len(projects) == 2

    @pytest.mark.asyncio
    async def test_get_by_workspace_with_skip_limit(self, db: AsyncSession):
        repo = ProjectRepository()
        await repo.create(db, workspace_id=WS_ID, name="P1")
        await repo.create(db, workspace_id=WS_ID, name="P2")
        projects = await repo.get_by_workspace(db, WS_ID, skip=1, limit=1)
        assert len(projects) == 1

    @pytest.mark.asyncio
    async def test_get_for_user(self, db: AsyncSession):
        repo = ProjectRepository()
        await repo.create(db, workspace_id=WS_ID, name="User Project")
        # get owner_id from the workspace created in fixture
        result = await db.execute(select(Workspace).where(Workspace.id == WS_ID))
        ws = result.scalar_one()
        projects = await repo.get_for_user(db, ws.owner_id)
        assert len(projects) >= 1

    @pytest.mark.asyncio
    async def test_update(self, db: AsyncSession):
        repo = ProjectRepository()
        p = await repo.create(db, workspace_id=WS_ID, name="Before")
        updated = await repo.update(db, p.id, name="After")
        assert updated.name == "After"

    @pytest.mark.asyncio
    async def test_delete(self, db: AsyncSession):
        repo = ProjectRepository()
        p = await repo.create(db, workspace_id=WS_ID, name="Delete Me")
        await repo.delete(db, p.id)
        with pytest.raises(NotFoundError):
            await repo.get(db, p.id)

    @pytest.mark.asyncio
    async def test_archive(self, db: AsyncSession):
        repo = ProjectRepository()
        p = await repo.create(db, workspace_id=WS_ID, name="Archive Me")
        archived = await repo.archive(db, p.id)
        assert archived.status == "archived"

    @pytest.mark.asyncio
    async def test_duplicate(self, db: AsyncSession):
        repo = ProjectRepository()
        p = await repo.create(
            db,
            workspace_id=WS_ID,
            name="Original",
            description="desc",
            research_goal="goal",
            key_questions={"q1": "a1"},
        )
        dup = await repo.duplicate(db, p.id, "Copy")
        assert dup.name == "Copy"
        assert dup.description == "desc"
        assert dup.research_goal == "goal"
        assert dup.key_questions == {"q1": "a1"}
        assert dup.id != p.id

    @pytest.mark.asyncio
    async def test_get_many_with_filters(self, db: AsyncSession):
        repo = ProjectRepository()
        await repo.create(db, workspace_id=WS_ID, name="Active", status="active")
        await repo.create(db, workspace_id=WS_ID, name="Archived", status="archived")
        active = await repo.get_many(db, workspace_id=WS_ID, status="active")
        assert len(active) == 1
        assert active[0].status == "active"

    @pytest.mark.asyncio
    async def test_exists(self, db: AsyncSession):
        repo = ProjectRepository()
        p = await repo.create(db, workspace_id=WS_ID, name="Exists")
        assert await repo.exists(db, p.id) is True
        assert await repo.exists(db, "nope") is False

    @pytest.mark.asyncio
    async def test_count(self, db: AsyncSession):
        repo = ProjectRepository()
        await repo.create(db, workspace_id=WS_ID, name="C1")
        await repo.create(db, workspace_id=WS_ID, name="C2")
        cnt = await repo.count(db, workspace_id=WS_ID)
        assert cnt == 2


class TestSessionRepository:
    @pytest.mark.asyncio
    async def test_create(self, db: AsyncSession):
        repo_p = ProjectRepository()
        p = await repo_p.create(db, workspace_id=WS_ID, name="Sess Proj")
        repo = SessionRepository()
        s = await repo.create(db, project_id=p.id, query="my query")
        assert s.id is not None
        assert s.status == "pending"
        assert s.total_tokens == 0

    @pytest.mark.asyncio
    async def test_create_custom(self, db: AsyncSession):
        repo_p = ProjectRepository()
        p = await repo_p.create(db, workspace_id=WS_ID, name="Sess Proj 2")
        repo = SessionRepository()
        s = await repo.create(
            db, project_id=p.id, query="q", status="running", total_tokens=500, total_cost=0.02
        )
        assert s.status == "running"
        assert s.total_tokens == 500

    @pytest.mark.asyncio
    async def test_get_by_project(self, db: AsyncSession):
        repo_p = ProjectRepository()
        p = await repo_p.create(db, workspace_id=WS_ID, name="Proj Sess")
        repo = SessionRepository()
        await repo.create(db, project_id=p.id, query="q1")
        await repo.create(db, project_id=p.id, query="q2")
        sessions = await repo.get_by_project(db, p.id)
        assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, db: AsyncSession):
        repo_p = ProjectRepository()
        p = await repo_p.create(db, workspace_id=WS_ID, name="Active Proj")
        repo = SessionRepository()
        await repo.create(db, project_id=p.id, query="running", status="running")
        await repo.create(db, project_id=p.id, query="pending", status="pending")
        await repo.create(db, project_id=p.id, query="done", status="completed")
        active = await repo.get_active_sessions(db, p.id)
        assert len(active) == 2

    @pytest.mark.asyncio
    async def test_get_recent_by_workspace(self, db: AsyncSession):
        repo_p = ProjectRepository()
        p = await repo_p.create(db, workspace_id=WS_ID, name="Recent Proj")
        repo = SessionRepository()
        await repo.create(db, project_id=p.id, query="q")
        recent = await repo.get_recent_by_workspace(db, WS_ID)
        assert len(recent) >= 1

    @pytest.mark.asyncio
    async def test_get_recent_by_workspace_limit(self, db: AsyncSession):
        repo_p = ProjectRepository()
        p = await repo_p.create(db, workspace_id=WS_ID, name="Recent Proj 2")
        repo = SessionRepository()
        for i in range(5):
            await repo.create(db, project_id=p.id, query=f"q{i}")
        recent = await repo.get_recent_by_workspace(db, WS_ID, limit=3)
        assert len(recent) == 3


class TestPaperRepository:
    @pytest.mark.asyncio
    async def test_create(self, db: AsyncSession):
        repo = PaperRepository()
        p = await repo.create(db, workspace_id=WS_ID, title="Test Paper", source="arxiv")
        assert p.id is not None
        assert p.status == "active"
        assert p.version == 1

    @pytest.mark.asyncio
    async def test_create_with_project(self, db: AsyncSession):
        repo_p = ProjectRepository()
        proj = await repo_p.create(db, workspace_id=WS_ID, name="Paper Proj")
        repo = PaperRepository()
        p = await repo.create(
            db, workspace_id=WS_ID, project_id=proj.id, title="Proj Paper", source="arxiv"
        )
        assert p.project_id == proj.id

    @pytest.mark.asyncio
    async def test_get_by_workspace(self, db: AsyncSession):
        repo = PaperRepository()
        await repo.create(db, workspace_id=WS_ID, title="P1", source="arxiv")
        await repo.create(db, workspace_id=WS_ID, title="P2", source="pubmed")
        papers = await repo.get_by_workspace(db, WS_ID)
        assert len(papers) == 2

    @pytest.mark.asyncio
    async def test_get_by_workspace_with_status(self, db: AsyncSession):
        repo = PaperRepository()
        await repo.create(db, workspace_id=WS_ID, title="Active", source="arxiv", status="active")
        await repo.create(
            db, workspace_id=WS_ID, title="Inactive", source="arxiv", status="inactive"
        )
        active = await repo.get_by_workspace(db, WS_ID, status="active")
        assert len(active) == 1
        assert active[0].status == "active"

    @pytest.mark.asyncio
    async def test_get_by_project(self, db: AsyncSession):
        repo_p = ProjectRepository()
        proj = await repo_p.create(db, workspace_id=WS_ID, name="Paper Proj 2")
        repo = PaperRepository()
        await repo.create(db, workspace_id=WS_ID, project_id=proj.id, title="P1", source="arxiv")
        await repo.create(db, workspace_id=WS_ID, project_id=proj.id, title="P2", source="arxiv")
        papers = await repo.get_by_project(db, proj.id)
        assert len(papers) == 2

    @pytest.mark.asyncio
    async def test_find_by_content_hash(self, db: AsyncSession):
        repo = PaperRepository()
        p = await repo.create(
            db, workspace_id=WS_ID, title="Hash Paper", source="arxiv", content_hash="abc123"
        )
        found = await repo.find_by_content_hash(db, "abc123", WS_ID)
        assert found is not None
        assert found.id == p.id
        not_found = await repo.find_by_content_hash(db, "nonexistent", WS_ID)
        assert not_found is None

    @pytest.mark.asyncio
    async def test_find_by_doi(self, db: AsyncSession):
        repo = PaperRepository()
        p = await repo.create(
            db, workspace_id=WS_ID, title="DOI Paper", source="arxiv", doi="10.1234/test"
        )
        found = await repo.find_by_doi(db, "10.1234/test", WS_ID)
        assert found is not None
        assert found.id == p.id
        not_found = await repo.find_by_doi(db, "10.9999/missing", WS_ID)
        assert not_found is None

    @pytest.mark.asyncio
    async def test_search(self, db: AsyncSession):
        repo = PaperRepository()
        await repo.create(
            db, workspace_id=WS_ID, title="Deep Learning", source="arxiv", abstract="neural networks"
        )
        await repo.create(
            db, workspace_id=WS_ID, title="Classical ML", source="arxiv", abstract="regression"
        )
        results = await repo.search(db, "deep", WS_ID)
        assert len(results) == 1
        assert results[0].title == "Deep Learning"

    @pytest.mark.asyncio
    async def test_search_by_abstract(self, db: AsyncSession):
        repo = PaperRepository()
        await repo.create(
            db, workspace_id=WS_ID, title="Paper A", source="arxiv", abstract="transformer attention"
        )
        results = await repo.search(db, "attention", WS_ID)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_no_results(self, db: AsyncSession):
        repo = PaperRepository()
        await repo.create(
            db, workspace_id=WS_ID, title="Paper", source="arxiv", abstract="test"
        )
        results = await repo.search(db, "zzzznotfound", WS_ID)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_update(self, db: AsyncSession):
        repo = PaperRepository()
        p = await repo.create(db, workspace_id=WS_ID, title="Before", source="arxiv")
        updated = await repo.update(db, p.id, title="After", citation_count=10)
        assert updated.title == "After"
        assert updated.citation_count == 10

    @pytest.mark.asyncio
    async def test_delete(self, db: AsyncSession):
        repo = PaperRepository()
        p = await repo.create(db, workspace_id=WS_ID, title="Delete Paper", source="arxiv")
        await repo.delete(db, p.id)
        with pytest.raises(NotFoundError):
            await repo.get(db, p.id)

    @pytest.mark.asyncio
    async def test_get_by_doi_alias(self, db: AsyncSession):
        repo = PaperRepository()
        p = await repo.create(
            db, workspace_id=WS_ID, title="Alias DOI", source="arxiv", doi="10.9999/alias"
        )
        found = await repo.get_by_doi(db, "10.9999/alias", WS_ID)
        assert found is not None
        assert found.id == p.id


class TestCitationRepository:
    @pytest.mark.asyncio
    async def test_create(self, db: AsyncSession):
        repo = CitationRepository()
        c = await repo.create(
            db, workspace_id=WS_ID, raw_citation_text="some text", title="My Citation"
        )
        assert c.id is not None
        assert c.style == "apa"
        assert c.source_type == "journal"

    @pytest.mark.asyncio
    async def test_create_with_paper(self, db: AsyncSession):
        repo_paper = PaperRepository()
        p = await repo_paper.create(db, workspace_id=WS_ID, title="Paper", source="arxiv")
        repo = CitationRepository()
        c = await repo.create(
            db,
            workspace_id=WS_ID,
            paper_id=p.id,
            raw_citation_text="ref",
            title="Paper Citation",
            style="mla",
        )
        assert c.paper_id == p.id
        assert c.style == "mla"

    @pytest.mark.asyncio
    async def test_get_by_workspace(self, db: AsyncSession):
        repo = CitationRepository()
        await repo.create(db, workspace_id=WS_ID, raw_citation_text="t1", title="C1")
        await repo.create(db, workspace_id=WS_ID, raw_citation_text="t2", title="C2")
        citations = await repo.get_by_workspace(db, WS_ID)
        assert len(citations) == 2

    @pytest.mark.asyncio
    async def test_get_by_paper(self, db: AsyncSession):
        repo_paper = PaperRepository()
        p = await repo_paper.create(db, workspace_id=WS_ID, title="Paper", source="arxiv")
        repo = CitationRepository()
        await repo.create(
            db, workspace_id=WS_ID, paper_id=p.id, raw_citation_text="r1", title="C1"
        )
        await repo.create(
            db, workspace_id=WS_ID, paper_id=p.id, raw_citation_text="r2", title="C2"
        )
        citations = await repo.get_by_paper(db, p.id)
        assert len(citations) == 2

    @pytest.mark.asyncio
    async def test_search(self, db: AsyncSession):
        repo = CitationRepository()
        await repo.create(
            db, workspace_id=WS_ID, raw_citation_text="some ref", title="Deep Learning Paper"
        )
        await repo.create(
            db, workspace_id=WS_ID, raw_citation_text="other ref", title="Biology Paper"
        )
        results = await repo.search(db, "Deep", WS_ID)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_by_formatted_citation(self, db: AsyncSession):
        repo = CitationRepository()
        await repo.create(
            db,
            workspace_id=WS_ID,
            raw_citation_text="raw",
            title="Paper",
            formatted_citation="Smith (2024) ...",
        )
        results = await repo.search(db, "Smith", WS_ID)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_count_by_style(self, db: AsyncSession):
        repo = CitationRepository()
        await repo.create(db, workspace_id=WS_ID, raw_citation_text="a", title="A", style="apa")
        await repo.create(db, workspace_id=WS_ID, raw_citation_text="b", title="B", style="apa")
        await repo.create(db, workspace_id=WS_ID, raw_citation_text="c", title="C", style="mla")
        counts = await repo.count_by_style(db, WS_ID)
        assert counts.get("apa") == 2
        assert counts.get("mla") == 1

    @pytest.mark.asyncio
    async def test_count_by_source_type(self, db: AsyncSession):
        repo = CitationRepository()
        await repo.create(
            db, workspace_id=WS_ID, raw_citation_text="a", title="A", source_type="journal"
        )
        await repo.create(
            db, workspace_id=WS_ID, raw_citation_text="b", title="B", source_type="journal"
        )
        await repo.create(
            db, workspace_id=WS_ID, raw_citation_text="c", title="C", source_type="book"
        )
        counts = await repo.count_by_source_type(db, WS_ID)
        assert counts.get("journal") == 2
        assert counts.get("book") == 1

    @pytest.mark.asyncio
    async def test_update(self, db: AsyncSession):
        repo = CitationRepository()
        c = await repo.create(
            db, workspace_id=WS_ID, raw_citation_text="original", title="Orig"
        )
        updated = await repo.update(db, c.id, title="Updated", year=2024)
        assert updated.title == "Updated"
        assert updated.year == 2024

    @pytest.mark.asyncio
    async def test_delete(self, db: AsyncSession):
        repo = CitationRepository()
        c = await repo.create(
            db, workspace_id=WS_ID, raw_citation_text="del", title="Delete Me"
        )
        await repo.delete(db, c.id)
        with pytest.raises(NotFoundError):
            await repo.get(db, c.id)


class TestDocumentRepository:
    @pytest.mark.asyncio
    async def test_create(self, db: AsyncSession):
        repo = DocumentRepository()
        d = await repo.create(
            db, workspace_id=WS_ID, title="My Doc", content="# Hello", format="markdown"
        )
        assert d.id is not None
        assert d.status == "draft"
        assert d.version == 1

    @pytest.mark.asyncio
    async def test_create_with_session(self, db: AsyncSession):
        repo_p = ProjectRepository()
        p = await repo_p.create(db, workspace_id=WS_ID, name="Doc Proj")
        repo_s = SessionRepository()
        s = await repo_s.create(db, project_id=p.id, query="q")
        repo = DocumentRepository()
        d = await repo.create(
            db,
            workspace_id=WS_ID,
            session_id=s.id,
            title="Session Doc",
            content="body",
            format="markdown",
        )
        assert d.session_id == s.id

    @pytest.mark.asyncio
    async def test_get_by_workspace(self, db: AsyncSession):
        repo = DocumentRepository()
        await repo.create(db, workspace_id=WS_ID, title="D1", content="c1", format="md")
        await repo.create(db, workspace_id=WS_ID, title="D2", content="c2", format="md")
        docs = await repo.get_by_workspace(db, WS_ID)
        assert len(docs) == 2

    @pytest.mark.asyncio
    async def test_get_by_session(self, db: AsyncSession):
        repo_p = ProjectRepository()
        p = await repo_p.create(db, workspace_id=WS_ID, name="Doc Proj 2")
        repo_s = SessionRepository()
        s = await repo_s.create(db, project_id=p.id, query="q")
        repo = DocumentRepository()
        await repo.create(
            db, workspace_id=WS_ID, session_id=s.id, title="D1", content="c1", format="md"
        )
        await repo.create(
            db, workspace_id=WS_ID, session_id=s.id, title="D2", content="c2", format="md"
        )
        docs = await repo.get_by_session(db, s.id)
        assert len(docs) == 2

    @pytest.mark.asyncio
    async def test_get_latest_by_workspace(self, db: AsyncSession):
        repo = DocumentRepository()
        await repo.create(db, workspace_id=WS_ID, title="Old", content="old", format="md")
        await repo.create(db, workspace_id=WS_ID, title="New", content="new", format="md")
        latest = await repo.get_latest_by_workspace(db, WS_ID)
        assert len(latest) >= 1
        assert latest[0].title == "New"

    @pytest.mark.asyncio
    async def test_get_latest_by_workspace_limit(self, db: AsyncSession):
        repo = DocumentRepository()
        for i in range(5):
            await repo.create(
                db, workspace_id=WS_ID, title=f"Doc {i}", content=str(i), format="md"
            )
        latest = await repo.get_latest_by_workspace(db, WS_ID, limit=3)
        assert len(latest) == 3

    @pytest.mark.asyncio
    async def test_update(self, db: AsyncSession):
        repo = DocumentRepository()
        d = await repo.create(
            db, workspace_id=WS_ID, title="Before", content="old", format="markdown"
        )
        updated = await repo.update(db, d.id, title="After", status="final")
        assert updated.title == "After"
        assert updated.status == "final"

    @pytest.mark.asyncio
    async def test_delete(self, db: AsyncSession):
        repo = DocumentRepository()
        d = await repo.create(
            db, workspace_id=WS_ID, title="Delete Doc", content="bye", format="md"
        )
        await repo.delete(db, d.id)
        with pytest.raises(NotFoundError):
            await repo.get(db, d.id)
