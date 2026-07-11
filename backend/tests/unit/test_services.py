from __future__ import annotations

import datetime
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import AgentContext
from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.models.citation import Citation
from app.models.document import Document
from app.models.research_paper import ResearchPaper
from app.models.research_project import ResearchProject
from app.models.research_session import ResearchSession
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.citation import (
    CitationCreate,
    CitationExportRequest,
    CitationUpdate,
)
from app.schemas.dashboard import (
    DashboardResponse,
    TokenUsageResponse,
    WorkflowStatusResponse,
)
from app.schemas.document import (
    DocumentExportResponse,
    DocumentGenerateRequest,
    DocumentResponse,
)
from app.schemas.library import (
    PaperResponse,
    PaperUpdate,
    PaperUploadResponse,
    PaperVersionResponse,
)
from app.schemas.research import (
    ResearchProjectCreate,
    ResearchProjectUpdate,
    ResearchSessionResponse,
    ResearchSubmission,
)
from app.schemas.search import SearchRequest, SearchResult
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate
from app.services.citation_service import CitationService
from app.services.dashboard_service import DashboardService
from app.services.document_service import DocumentService
from app.services.library_service import LibraryService
from app.services.paper_service import PaperService
from app.services.project_service import ProjectService
from app.services.research_service import ResearchService
from app.services.search_service import SearchService
from app.services.workspace_service import WorkspaceService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_workspace(**kw) -> Workspace:
    defaults = dict(
        id="ws-1",
        owner_id="user-1",
        name="Test Workspace",
        description="A workspace",
        research_topic="AI",
        status="active",
        created_at=datetime.datetime.now(datetime.UTC),
        updated_at=datetime.datetime.now(datetime.UTC),
    )
    defaults.update(kw)
    name_val = defaults.pop("name", "Test Workspace")
    m = MagicMock(spec=Workspace, **defaults)
    m.name = name_val
    return m


def _make_workspace_member(**kw) -> WorkspaceMember:
    defaults = dict(workspace_id="ws-1", user_id="user-2", role="editor")
    defaults.update(kw)
    return MagicMock(spec=WorkspaceMember, **defaults)


def _make_project(**kw) -> ResearchProject:
    defaults = dict(
        id="proj-1",
        workspace_id="ws-1",
        name="Test Project",
        description="A project",
        status="active",
        research_goal="Goal",
        key_questions=["q1"],
        created_at=datetime.datetime.now(datetime.UTC),
        updated_at=datetime.datetime.now(datetime.UTC),
    )
    defaults.update(kw)
    name_val = defaults.pop("name", "Test Project")
    m = MagicMock(spec=ResearchProject, **defaults)
    m.name = name_val
    return m


def _make_session(**kw) -> ResearchSession:
    defaults = dict(
        id="sess-1",
        project_id="proj-1",
        status="completed",
        workflow_id="wf-1",
        query="test query",
        agent_phases_completed=["research", "analysis"],
        total_tokens=1000,
        total_cost=0.05,
        started_at=datetime.datetime.now(datetime.UTC),
        completed_at=datetime.datetime.now(datetime.UTC),
        error_message=None,
        created_at=datetime.datetime.now(datetime.UTC),
    )
    defaults.update(kw)
    return MagicMock(spec=ResearchSession, **defaults)


def _make_paper(**kw) -> ResearchPaper:
    defaults = dict(
        id="paper-1",
        workspace_id="ws-1",
        project_id=None,
        title="Test Paper",
        authors=["Smith, J"],
        abstract="An abstract",
        source="upload",
        file_path="/tmp/test.pdf",
        file_type="pdf",
        file_size=1024,
        doi="10.1234/test",
        arxiv_id=None,
        url=None,
        publication_year=2024,
        venue="Journal",
        citation_count=5,
        status="active",
        version=1,
        content_hash="abc123",
        created_at=datetime.datetime.now(datetime.UTC),
        updated_at=datetime.datetime.now(datetime.UTC),
    )
    defaults.update(kw)
    return MagicMock(spec=ResearchPaper, **defaults)


def _make_citation(**kw) -> Citation:
    defaults = dict(
        id="cit-1",
        workspace_id="ws-1",
        paper_id="paper-1",
        raw_citation_text="Test citation",
        formatted_citation="Formatted (2024).",
        style="apa",
        source_type="journal",
        authors=["Smith, J"],
        title="A Title",
        year=2024,
        journal="Journal",
        volume="10",
        issue="2",
        pages="100-110",
        doi="10.1234/test",
        url="",
        isbn="",
        publisher="",
        accessed_date=None,
        created_at=datetime.datetime.now(datetime.UTC),
        updated_at=datetime.datetime.now(datetime.UTC),
    )
    defaults.update(kw)
    return MagicMock(spec=Citation, **defaults)


def _make_document(**kw) -> Document:
    defaults = dict(
        id="doc-1",
        workspace_id="ws-1",
        session_id="sess-1",
        format="markdown",
        title="Test Doc",
        content="# Title\n\nContent.",
        file_path="/tmp/doc.md",
        file_size=50,
        status="completed",
        version=1,
        citation_count=3,
        template_used="default",
        created_at=datetime.datetime.now(datetime.UTC),
        updated_at=datetime.datetime.now(datetime.UTC),
    )
    defaults.update(kw)
    return MagicMock(spec=Document, **defaults)


# ===================================================================
# Fixtures
# ===================================================================

@pytest.fixture
def db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def ws_repo():
    return AsyncMock()


@pytest.fixture
def project_repo():
    return AsyncMock()


@pytest.fixture
def paper_repo():
    return AsyncMock()


@pytest.fixture
def citation_repo():
    return AsyncMock()


@pytest.fixture
def session_repo():
    return AsyncMock()


@pytest.fixture
def document_repo():
    return AsyncMock()


@pytest.fixture
def workflow_engine():
    return AsyncMock()


@pytest.fixture
def supervisor():
    return AsyncMock()


@pytest.fixture
def event_manager():
    manager = AsyncMock()
    # Real EventStreamManager.get_event_history returns a list; a bare
    # AsyncMock's default return value is a MagicMock, which isn't
    # iterable and breaks any `for event in ...` consumer (e.g.
    # ResearchService._persist_phase_results). Tests that care about
    # specific events override this explicitly.
    manager.get_event_history = AsyncMock(return_value=[])
    return manager


@pytest.fixture
def agent_registry():
    return MagicMock()


@pytest.fixture
def writing_agent():
    return AsyncMock()


@pytest.fixture
def vector_search():
    return AsyncMock()


@pytest.fixture
def conversation_repo():
    return AsyncMock()


# ---------------------------------------------------------------------------
# WorkspaceService
# ---------------------------------------------------------------------------

@pytest.fixture
def workspace_service(ws_repo, project_repo, paper_repo, citation_repo):
    svc = WorkspaceService(
        repo=ws_repo,
        project_repo=project_repo,
        paper_repo=paper_repo,
        citation_repo=citation_repo,
    )
    svc._count_sessions = AsyncMock(return_value=0)
    return svc


class TestWorkspaceService:
    async def test_create_workspace_success(
        self, workspace_service, db, ws_repo
    ):
        ws_mock = _make_workspace()
        ws_repo.create = AsyncMock(return_value=ws_mock)
        ws_repo.add_member = AsyncMock()
        ws_repo.get_member_count = AsyncMock(return_value=1)

        data = WorkspaceCreate(name="New WS", description="desc", research_topic="AI")
        result = await workspace_service.create_workspace(db, "user-1", data)

        assert result.name == "Test Workspace"
        ws_repo.create.assert_awaited_once()
        ws_repo.add_member.assert_awaited_once_with(db, ws_mock.id, "user-1", role="owner")

    async def test_get_workspace_success(self, workspace_service, db, ws_repo, paper_repo):
        ws = _make_workspace(owner_id="user-1")
        ws_repo.get = AsyncMock(return_value=ws)
        ws_repo.get_member_count = AsyncMock(return_value=2)
        paper_repo.get_by_workspace = AsyncMock(return_value=[_make_paper()])

        result = await workspace_service.get_workspace(db, "ws-1", "user-1")

        assert result.id == "ws-1"
        assert result.member_count == 2

    async def test_get_workspace_unauthorized(self, workspace_service, db, ws_repo):
        ws = _make_workspace(owner_id="owner-1")
        ws_repo.get = AsyncMock(return_value=ws)
        ws_repo.get_member_role = AsyncMock(return_value=None)

        with pytest.raises(AuthorizationError, match="does not have access"):
            await workspace_service.get_workspace(db, "ws-1", "user-2")

    async def test_update_workspace_success(self, workspace_service, db, ws_repo, paper_repo):
        ws = _make_workspace(owner_id="user-1", name="Old")
        ws_repo.get = AsyncMock(return_value=ws)
        ws_repo.update = AsyncMock(return_value=_make_workspace(name="Updated"))
        ws_repo.get_member_count = AsyncMock(return_value=1)
        paper_repo.get_by_workspace = AsyncMock(return_value=[])

        data = WorkspaceUpdate(name="Updated")
        result = await workspace_service.update_workspace(db, "ws-1", "user-1", data)

        assert result.name == "Updated"

    async def test_update_workspace_not_owner(self, workspace_service, db, ws_repo):
        ws = _make_workspace(owner_id="owner-1")
        ws_repo.get = AsyncMock(return_value=ws)

        data = WorkspaceUpdate(name="Updated")
        with pytest.raises(AuthorizationError, match="Only the workspace owner"):
            await workspace_service.update_workspace(db, "ws-1", "user-2", data)

    async def test_delete_workspace_success(self, workspace_service, db, ws_repo):
        ws = _make_workspace(owner_id="user-1")
        ws_repo.get = AsyncMock(return_value=ws)
        ws_repo.delete = AsyncMock()

        await workspace_service.delete_workspace(db, "ws-1", "user-1")
        ws_repo.delete.assert_awaited_once_with(db, "ws-1")

    async def test_delete_workspace_not_owner(self, workspace_service, db, ws_repo):
        ws = _make_workspace(owner_id="owner-1")
        ws_repo.get = AsyncMock(return_value=ws)

        with pytest.raises(AuthorizationError, match="Only the workspace owner"):
            await workspace_service.delete_workspace(db, "ws-1", "user-2")

    async def test_list_workspaces_success(self, workspace_service, db, ws_repo, paper_repo):
        ws1 = _make_workspace(id="ws-1", name="WS1")
        ws2 = _make_workspace(id="ws-2", name="WS2")
        ws_repo.get_for_user = AsyncMock(return_value=[ws1, ws2])
        ws_repo.get_member_count = AsyncMock(return_value=1)
        paper_repo.get_by_workspace = AsyncMock(return_value=[])
        workspace_service._count_sessions = AsyncMock(return_value=0)

        results, total = await workspace_service.list_workspaces(db, "user-1", 0, 10)

        assert total == 2
        assert len(results) == 2

    async def test_add_member_success(self, workspace_service, db, ws_repo):
        ws = _make_workspace(owner_id="user-1")
        ws_repo.get = AsyncMock(return_value=ws)
        member = _make_workspace_member()
        ws_repo.add_member = AsyncMock(return_value=member)

        result = await workspace_service.add_member(db, "ws-1", "user-1", "user-2", "editor")
        assert result.role == "editor"

    async def test_add_member_not_owner(self, workspace_service, db, ws_repo):
        ws = _make_workspace(owner_id="owner-1")
        ws_repo.get = AsyncMock(return_value=ws)

        with pytest.raises(AuthorizationError, match="Only the workspace owner"):
            await workspace_service.add_member(db, "ws-1", "user-2", "user-3", "editor")

    async def test_remove_member_success(self, workspace_service, db, ws_repo):
        ws = _make_workspace(owner_id="user-1")
        ws_repo.get = AsyncMock(return_value=ws)
        ws_repo.remove_member = AsyncMock()

        await workspace_service.remove_member(db, "ws-1", "user-1", "user-2")
        ws_repo.remove_member.assert_awaited_once_with(db, "ws-1", "user-2")

    async def test_remove_member_not_owner(self, workspace_service, db, ws_repo):
        ws = _make_workspace(owner_id="owner-1")
        ws_repo.get = AsyncMock(return_value=ws)

        with pytest.raises(AuthorizationError, match="Only the workspace owner"):
            await workspace_service.remove_member(db, "ws-1", "user-2", "user-3")

    async def test_get_member_role(self, workspace_service, db, ws_repo):
        ws_repo.get_member_role = AsyncMock(return_value="editor")
        role = await workspace_service.get_member_role(db, "ws-1", "user-2")
        assert role == "editor"


# ---------------------------------------------------------------------------
# ProjectService
# ---------------------------------------------------------------------------

@pytest.fixture
def project_service(project_repo, ws_repo):
    svc = ProjectService(repo=project_repo, workspace_repo=ws_repo)
    svc._count_sessions = AsyncMock(return_value=0)
    return svc


class TestProjectService:
    async def test_create_project_success(self, project_service, db, project_repo, ws_repo):
        ws = _make_workspace(owner_id="user-1")
        ws_repo.get = AsyncMock(return_value=ws)
        proj = _make_project()
        project_repo.create = AsyncMock(return_value=proj)

        data = ResearchProjectCreate(workspace_id="ws-1", name="Proj", description="d")
        result = await project_service.create_project(db, "user-1", data)

        assert result.name == "Test Project"

    async def test_create_project_no_access(self, project_service, db, ws_repo):
        ws = _make_workspace(owner_id="owner-1")
        ws_repo.get = AsyncMock(return_value=ws)
        ws_repo.get_member_role = AsyncMock(return_value=None)

        data = ResearchProjectCreate(workspace_id="ws-1", name="Proj")
        with pytest.raises(AuthorizationError, match="does not have access"):
            await project_service.create_project(db, "user-2", data)

    async def test_get_project_success(self, project_service, db, project_repo, ws_repo):
        proj = _make_project()
        project_repo.get = AsyncMock(return_value=proj)
        ws = _make_workspace(owner_id="user-1")
        ws_repo.get = AsyncMock(return_value=ws)

        result = await project_service.get_project(db, "proj-1", "user-1")
        assert result.id == "proj-1"

    async def test_get_project_not_found(self, project_service, db, project_repo):
        project_repo.get = AsyncMock(side_effect=NotFoundError("ResearchProject", "bad"))
        with pytest.raises(NotFoundError):
            await project_service.get_project(db, "bad", "user-1")

    async def test_update_project_success(self, project_service, db, project_repo, ws_repo):
        proj = _make_project()
        project_repo.get = AsyncMock(return_value=proj)
        ws = _make_workspace(owner_id="user-1")
        ws_repo.get = AsyncMock(return_value=ws)
        project_repo.update = AsyncMock(return_value=_make_project(name="Updated"))

        data = ResearchProjectUpdate(name="Updated")
        result = await project_service.update_project(db, "proj-1", "user-1", data)
        assert result.name == "Updated"

    async def test_delete_project_success(self, project_service, db, project_repo, ws_repo):
        proj = _make_project()
        project_repo.get = AsyncMock(return_value=proj)
        ws = _make_workspace(owner_id="user-1")
        ws_repo.get = AsyncMock(return_value=ws)
        project_repo.delete = AsyncMock()

        await project_service.delete_project(db, "proj-1", "user-1")
        project_repo.delete.assert_awaited_once_with(db, "proj-1")

    async def test_archive_project_success(self, project_service, db, project_repo, ws_repo):
        proj = _make_project()
        project_repo.get = AsyncMock(return_value=proj)
        ws = _make_workspace(owner_id="user-1")
        ws_repo.get = AsyncMock(return_value=ws)
        archived = _make_project(status="archived")
        project_repo.archive = AsyncMock(return_value=archived)

        result = await project_service.archive_project(db, "proj-1", "user-1")
        assert result.status == "archived"

    async def test_duplicate_project_success(self, project_service, db, project_repo, ws_repo):
        proj = _make_project(name="Original")
        project_repo.get = AsyncMock(return_value=proj)
        ws = _make_workspace(owner_id="user-1")
        ws_repo.get = AsyncMock(return_value=ws)
        dup = _make_project(name="Original (Copy)")
        project_repo.duplicate = AsyncMock(return_value=dup)

        result = await project_service.duplicate_project(db, "proj-1", "user-1")
        assert result.name == "Original (Copy)"

    async def test_duplicate_project_with_custom_name(self, project_service, db, project_repo, ws_repo):
        proj = _make_project(name="Original")
        project_repo.get = AsyncMock(return_value=proj)
        ws = _make_workspace(owner_id="user-1")
        ws_repo.get = AsyncMock(return_value=ws)
        dup = _make_project(name="Custom Copy")
        project_repo.duplicate = AsyncMock(return_value=dup)

        result = await project_service.duplicate_project(db, "proj-1", "user-1", new_name="Custom Copy")
        assert result.name == "Custom Copy"

    async def test_list_projects_success(self, project_service, db, project_repo, ws_repo):
        ws = _make_workspace(owner_id="user-1")
        ws_repo.get = AsyncMock(return_value=ws)
        proj1 = _make_project(id="p1")
        proj2 = _make_project(id="p2")
        project_repo.get_by_workspace = AsyncMock(return_value=[proj1, proj2])

        results, total = await project_service.list_projects(db, "ws-1", "user-1", 0, 10)
        assert total == 2
        assert len(results) == 2


# ---------------------------------------------------------------------------
# ResearchService
# ---------------------------------------------------------------------------

@pytest.fixture
def research_service(session_repo, project_repo, workflow_engine, supervisor, event_manager, agent_registry):
    return ResearchService(
        session_repo=session_repo,
        project_repo=project_repo,
        workflow_engine=workflow_engine,
        supervisor=supervisor,
        event_manager=event_manager,
        registry=agent_registry,
    )


class TestResearchService:
    async def test_submit_query_success(self, research_service, db, session_repo, project_repo, workflow_engine, supervisor):
        proj = _make_project(workspace_id="ws-1")
        project_repo.get = AsyncMock(return_value=proj)
        sess = _make_session()
        session_repo.create = AsyncMock(return_value=sess)
        session_repo.update = AsyncMock()
        workflow_engine.create_workflow = AsyncMock(return_value="wf-1")
        supervisor.execute = AsyncMock()

        with (
            patch("app.repositories.WorkspaceRepository") as mock_ws_cls,
            patch("app.services.research_service.asyncio.create_task") as mock_create_task,
        ):
            mock_ws = AsyncMock()
            mock_ws.get = AsyncMock(return_value=_make_workspace(owner_id="user-1"))
            mock_ws_cls.return_value = mock_ws

            data = ResearchSubmission(query="test query", project_id="proj-1")
            result = await research_service.submit_query(db, "user-1", data)

        assert result.status == "running"
        assert result.session_id == sess.id
        assert result.workflow_id == "wf-1"
        mock_create_task.assert_called_once()
        mock_create_task.call_args[0][0].close()

    async def test_run_workflow_in_background_success(self, research_service, session_repo, supervisor):
        supervisor.execute = AsyncMock()
        session_repo.update = AsyncMock()
        fake_db = AsyncMock()

        with patch("app.core.database.get_db_manager") as mock_get_mgr:
            mock_mgr = MagicMock()
            mock_mgr.create_session = MagicMock(return_value=fake_db)
            mock_get_mgr.return_value = mock_mgr

            context = AgentContext(workflow_id="wf-1", step_id="supervisor", trace_id="t-1", input={})
            await research_service._run_workflow_in_background("sess-1", context)

        supervisor.execute.assert_awaited_once_with(context)
        session_repo.update.assert_awaited_once()
        _, kwargs = session_repo.update.call_args
        assert kwargs["status"] == "completed"
        fake_db.commit.assert_awaited_once()
        fake_db.close.assert_awaited_once()

    async def test_run_workflow_in_background_persists_phase_results(
        self, research_service, session_repo, supervisor, event_manager
    ):
        # Regression test: the automatic pipeline (submit_query ->
        # SupervisorAgent.execute) previously never populated
        # session.results, so Gap Analysis / Research Ideas tabs (which
        # read session.results.analysis / .idea_gen) stayed empty even
        # after the pipeline had actually produced that output. Verifies
        # _persist_phase_results backfills it from the SSE event history.
        from app.streaming.events import EventType

        supervisor.execute = AsyncMock()
        session_repo.update = AsyncMock()
        session_repo.get = AsyncMock(return_value=_make_session(results=None))
        fake_db = AsyncMock()

        research_event = MagicMock()
        research_event.type = EventType.AGENT_COMPLETED
        research_event.agent_id = "Research"
        research_event.data = {"summary": "Found 5 papers", "result": {"paper_collection": {"papers": []}}}

        analysis_event = MagicMock()
        analysis_event.type = EventType.AGENT_COMPLETED
        analysis_event.agent_id = "Analysis"
        analysis_event.data = {"summary": "3 gaps", "result": {"analysis_report": {"gaps": []}}}

        planner_event = MagicMock()
        planner_event.type = EventType.AGENT_COMPLETED
        planner_event.agent_id = "Planner"
        planner_event.data = {"has_plan": True, "summary": "Plan ready"}

        event_manager.get_event_history = AsyncMock(
            return_value=[planner_event, research_event, analysis_event]
        )

        with patch("app.core.database.get_db_manager") as mock_get_mgr:
            mock_mgr = MagicMock()
            mock_mgr.create_session = MagicMock(return_value=fake_db)
            mock_get_mgr.return_value = mock_mgr

            context = AgentContext(workflow_id="wf-1", step_id="supervisor", trace_id="t-1", input={})
            await research_service._run_workflow_in_background("sess-1", context)

        saved_results = [
            call.kwargs["results"]
            for call in session_repo.update.call_args_list
            if "results" in call.kwargs
        ]
        assert len(saved_results) == 2
        assert "research" in saved_results[0]
        assert "analysis" in saved_results[1]
        assert saved_results[1]["analysis"] == {"analysis_report": {"gaps": []}}

    async def test_run_workflow_in_background_marks_session_failed_on_error(
        self, research_service, session_repo, supervisor
    ):
        supervisor.execute = AsyncMock(side_effect=RuntimeError("boom"))
        session_repo.update = AsyncMock()
        fake_db = AsyncMock()

        with patch("app.core.database.get_db_manager") as mock_get_mgr:
            mock_mgr = MagicMock()
            mock_mgr.create_session = MagicMock(return_value=fake_db)
            mock_get_mgr.return_value = mock_mgr

            context = AgentContext(workflow_id="wf-1", step_id="supervisor", trace_id="t-1", input={})
            await research_service._run_workflow_in_background("sess-1", context)

        session_repo.update.assert_awaited_once()
        _, kwargs = session_repo.update.call_args
        assert kwargs["status"] == "failed"
        assert "boom" in kwargs["error_message"]
        fake_db.rollback.assert_awaited()
        fake_db.close.assert_awaited_once()

    async def test_submit_query_rejects_malicious_input(self, research_service, db):
        data = ResearchSubmission(query="<script>alert(1)</script>", project_id="proj-1")
        with pytest.raises(ValidationError):
            await research_service.submit_query(db, "user-1", data)

    async def test_submit_query_unauthorized(self, research_service, db, project_repo):
        proj = _make_project(workspace_id="ws-1")
        project_repo.get = AsyncMock(return_value=proj)

        with patch("app.repositories.WorkspaceRepository") as mock_ws_cls:
            mock_ws = AsyncMock()
            mock_ws.get = AsyncMock(return_value=_make_workspace(owner_id="owner-1"))
            mock_ws_cls.return_value = mock_ws
            mock_ws.get_member_role = AsyncMock(return_value=None)

            data = ResearchSubmission(query="q", project_id="proj-1")
            with pytest.raises(AuthorizationError, match="does not have access"):
                await research_service.submit_query(db, "user-2", data)

    async def test_get_session_success(self, research_service, db, session_repo, project_repo):
        sess = _make_session(agent_phases_completed=["research"])
        session_repo.get = AsyncMock(return_value=sess)
        proj = _make_project()
        project_repo.get = AsyncMock(return_value=proj)

        with patch("app.repositories.WorkspaceRepository") as mock_ws_cls:
            mock_ws = AsyncMock()
            mock_ws.get = AsyncMock(return_value=_make_workspace(owner_id="user-1"))
            mock_ws_cls.return_value = mock_ws

            result = await research_service.get_session(db, "sess-1", "user-1")

        assert result.id == "sess-1"
        assert result.query == "test query"
        assert result.agent_phases_completed == 1

    async def test_get_session_not_found(self, research_service, db, session_repo):
        session_repo.get = AsyncMock(side_effect=NotFoundError("ResearchSession", "bad"))
        with pytest.raises(NotFoundError):
            await research_service.get_session(db, "bad", "user-1")

    async def test_list_sessions_success(self, research_service, db, session_repo, project_repo):
        proj = _make_project()
        project_repo.get = AsyncMock(return_value=proj)
        s1 = _make_session(id="s1")
        s2 = _make_session(id="s2")
        session_repo.get_by_project = AsyncMock(return_value=[s1, s2])

        with patch("app.repositories.WorkspaceRepository") as mock_ws_cls:
            mock_ws = AsyncMock()
            mock_ws.get = AsyncMock(return_value=_make_workspace(owner_id="user-1"))
            mock_ws_cls.return_value = mock_ws

            results, total = await research_service.list_sessions(db, "proj-1", "user-1", 0, 10)
        assert total == 2
        assert len(results) == 2

    async def test_upload_paper_success(self, research_service, db):
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=b"pdf content")
        mock_file.filename = "test.pdf"

        with patch("app.repositories.WorkspaceRepository") as mock_ws_cls:
            mock_ws = AsyncMock()
            mock_ws.get = AsyncMock(return_value=_make_workspace(owner_id="user-1"))
            mock_ws_cls.return_value = mock_ws
            with patch("app.services.research_service.PaperRepository") as mock_paper_cls:
                mock_paper = AsyncMock()
                mock_paper.create = AsyncMock(return_value=_make_paper())
                mock_paper_cls.return_value = mock_paper
                with patch("app.services.research_service.os.makedirs"):
                    with patch("app.services.research_service.open", MagicMock()):
                        result = await research_service.upload_paper(db, "ws-1", "user-1", mock_file)
        assert isinstance(result, PaperUploadResponse)

    async def test_trigger_retrieval_success(self, research_service, db, session_repo, project_repo, agent_registry):
        sess = _make_session(workflow_id="wf-1")
        session_repo.get = AsyncMock(return_value=sess)
        proj = _make_project()
        project_repo.get = AsyncMock(return_value=proj)
        agent = AsyncMock()
        agent_registry.get = MagicMock(return_value=agent)

        with patch("app.repositories.WorkspaceRepository") as mock_ws_cls:
            mock_ws = AsyncMock()
            mock_ws.get = AsyncMock(return_value=_make_workspace(owner_id="user-1"))
            mock_ws_cls.return_value = mock_ws
            with patch.object(research_service, "get_session", AsyncMock(return_value=_make_session_response())):
                await research_service.trigger_retrieval(db, "sess-1", "user-1")

        agent_registry.get.assert_called_with("research")
        agent.execute.assert_awaited_once()

    async def test_trigger_analysis_success(self, research_service, db, session_repo, project_repo, agent_registry):
        sess = _make_session(workflow_id="wf-1")
        session_repo.get = AsyncMock(return_value=sess)
        proj = _make_project()
        project_repo.get = AsyncMock(return_value=proj)
        agent = AsyncMock()
        agent_registry.get = MagicMock(return_value=agent)

        with patch("app.repositories.WorkspaceRepository") as mock_ws_cls:
            mock_ws = AsyncMock()
            mock_ws.get = AsyncMock(return_value=_make_workspace(owner_id="user-1"))
            mock_ws_cls.return_value = mock_ws
            with patch.object(research_service, "get_session", AsyncMock(return_value=_make_session_response())):
                await research_service.trigger_analysis(db, "sess-1", "user-1")

        agent_registry.get.assert_called_with("analysis")

    async def test_trigger_writing_success(self, research_service, db, session_repo, project_repo, agent_registry):
        sess = _make_session(workflow_id="wf-1")
        session_repo.get = AsyncMock(return_value=sess)
        proj = _make_project()
        project_repo.get = AsyncMock(return_value=proj)
        agent = AsyncMock()
        agent_registry.get = MagicMock(return_value=agent)

        with patch("app.repositories.WorkspaceRepository") as mock_ws_cls:
            mock_ws = AsyncMock()
            mock_ws.get = AsyncMock(return_value=_make_workspace(owner_id="user-1"))
            mock_ws_cls.return_value = mock_ws
            with patch.object(research_service, "get_session", AsyncMock(return_value=_make_session_response())):
                await research_service.trigger_writing(db, "sess-1", "user-1")

        agent_registry.get.assert_called_with("writing")

    async def test_trigger_retrieval_unauthorized(self, research_service, db, session_repo, project_repo):
        sess = _make_session()
        session_repo.get = AsyncMock(return_value=sess)
        proj = _make_project()
        project_repo.get = AsyncMock(return_value=proj)

        with patch("app.repositories.WorkspaceRepository") as mock_ws_cls:
            mock_ws = AsyncMock()
            mock_ws.get = AsyncMock(return_value=_make_workspace(owner_id="owner-1"))
            mock_ws_cls.return_value = mock_ws
            mock_ws.get_member_role = AsyncMock(return_value=None)

            with pytest.raises(AuthorizationError):
                await research_service.trigger_retrieval(db, "sess-1", "user-2")

    async def test_get_overview_success(self, research_service, db, project_repo, session_repo):
        active_proj = _make_project(id="proj-1", status="active")
        archived_proj = _make_project(id="proj-2", status="archived")
        project_repo.get_by_workspace_ids = AsyncMock(return_value=[active_proj, archived_proj])
        session_repo.get_by_project_ids = AsyncMock(return_value=[])

        with patch("app.services.research_service.WorkspaceRepository") as mock_ws_cls, \
                patch("app.services.research_service.PaperRepository") as mock_paper_cls:
            mock_ws = AsyncMock()
            mock_ws.get_for_user = AsyncMock(return_value=[_make_workspace(id="ws-1")])
            mock_ws_cls.return_value = mock_ws

            mock_paper = AsyncMock()
            mock_paper.get_by_workspace_ids = AsyncMock(return_value=[_make_paper(), _make_paper(id="paper-2")])
            mock_paper_cls.return_value = mock_paper

            result = await research_service.get_overview(db, "user-1")

        assert result["projects"] == 2
        assert result["papers"] == 2
        assert result["activeProjects"] == 1
        assert result["completedProjects"] == 1
        assert result["staleProjects"] == 1
        assert result["inProgressProjects"] == 0

    async def test_get_activity_success(self, research_service, db, project_repo):
        proj = _make_project(id="proj-1")
        project_repo.get_by_workspace_ids = AsyncMock(return_value=[proj])

        with patch("app.services.research_service.WorkspaceRepository") as mock_ws_cls:
            mock_ws = AsyncMock()
            mock_ws.get_for_user = AsyncMock(return_value=[_make_workspace(id="ws-1")])
            mock_ws_cls.return_value = mock_ws

            result = await research_service.get_activity(db, "user-1")

        assert len(result["recentlyOpened"]) == 1
        assert result["recentlyOpened"][0]["id"] == "proj-1"

    async def test_get_cards_only_includes_active(self, research_service, db, project_repo):
        active_proj = _make_project(id="proj-1", status="active")
        archived_proj = _make_project(id="proj-2", status="archived")
        project_repo.get_by_workspace_ids = AsyncMock(return_value=[active_proj, archived_proj])

        with patch("app.services.research_service.WorkspaceRepository") as mock_ws_cls:
            mock_ws = AsyncMock()
            mock_ws.get_for_user = AsyncMock(return_value=[_make_workspace(id="ws-1")])
            mock_ws_cls.return_value = mock_ws

            result = await research_service.get_cards(db, "user-1")

        assert len(result) == 1
        assert result[0]["id"] == "proj-1"
        assert result[0]["type"] == "project"

    async def test_get_recent_activity_combines_sessions_and_papers(
        self, research_service, db, session_repo
    ):
        session_repo.get_recent_by_workspace_ids = AsyncMock(return_value=[_make_session()])

        with patch("app.services.research_service.WorkspaceRepository") as mock_ws_cls, \
                patch("app.services.research_service.PaperRepository") as mock_paper_cls:
            mock_ws = AsyncMock()
            mock_ws.get_for_user = AsyncMock(return_value=[_make_workspace(id="ws-1")])
            mock_ws_cls.return_value = mock_ws

            mock_paper = AsyncMock()
            mock_paper.get_by_workspace_ids = AsyncMock(return_value=[_make_paper()])
            mock_paper_cls.return_value = mock_paper

            result = await research_service.get_recent_activity(db, "user-1")

        assert len(result) == 2
        types = {e["type"] for e in result}
        assert types == {"task", "paper"}

    async def test_get_notes_reading_queue_saved_papers_are_empty(self, research_service, db):
        assert await research_service.get_notes(db, "user-1") == []
        assert await research_service.get_reading_queue(db, "user-1") == []
        assert await research_service.get_saved_papers(db, "user-1") == []


def _make_session_response(**kw) -> ResearchSessionResponse:
    defaults = dict(
        id="sess-1", project_id="proj-1", status="running", workflow_id="wf-1",
        query="q", agent_phases_completed=0, total_tokens=0, total_cost=0.0,
        started_at=None, completed_at=None, error_message=None, created_at=None,
    )
    defaults.update(kw)
    return ResearchSessionResponse(**defaults)


# ---------------------------------------------------------------------------
# CitationService
# ---------------------------------------------------------------------------

@pytest.fixture
def citation_service(citation_repo, paper_repo):
    return CitationService(repo=citation_repo, paper_repo=paper_repo)


class TestCitationService:
    async def test_create_citation_success(self, citation_service, db, citation_repo):
        cit = _make_citation()
        citation_repo.create = AsyncMock(return_value=cit)
        citation_repo.update = AsyncMock(return_value=cit)

        with patch.object(citation_service, "_verify_workspace_access", AsyncMock()):
            data = CitationCreate(title="Test", authors=["Smith, J"], year=2024)
            result = await citation_service.create_citation(db, "ws-1", "user-1", data)

        assert result.title == "A Title"
        assert citation_repo.create.called

    async def test_create_citation_unauthorized(self, citation_service, db):
        with patch.object(citation_service, "_verify_workspace_access", AsyncMock(side_effect=AuthorizationError("no"))):
            data = CitationCreate(title="Test")
            with pytest.raises(AuthorizationError):
                await citation_service.create_citation(db, "ws-1", "user-2", data)

    async def test_update_citation_success(self, citation_service, db, citation_repo):
        cit = _make_citation()
        citation_repo.get = AsyncMock(return_value=cit)
        updated = _make_citation(title="Updated")
        citation_repo.update = AsyncMock(return_value=updated)

        with patch.object(citation_service, "_verify_workspace_access", AsyncMock()):
            data = CitationUpdate(title="Updated")
            result = await citation_service.update_citation(db, "cit-1", "user-1", data)

        assert result.title == "Updated"

    async def test_update_citation_no_changes(self, citation_service, db, citation_repo):
        cit = _make_citation()
        citation_repo.get = AsyncMock(return_value=cit)

        with patch.object(citation_service, "_verify_workspace_access", AsyncMock()):
            data = CitationUpdate()
            result = await citation_service.update_citation(db, "cit-1", "user-1", data)
        assert result.title == "A Title"

    async def test_delete_citation_success(self, citation_service, db, citation_repo):
        cit = _make_citation()
        citation_repo.get = AsyncMock(return_value=cit)
        citation_repo.delete = AsyncMock()

        with patch.object(citation_service, "_verify_workspace_access", AsyncMock()):
            await citation_service.delete_citation(db, "cit-1", "user-1")
        citation_repo.delete.assert_awaited_once_with(db, "cit-1")

    async def test_get_citation_success(self, citation_service, db, citation_repo):
        cit = _make_citation()
        citation_repo.get = AsyncMock(return_value=cit)

        with patch.object(citation_service, "_verify_workspace_access", AsyncMock()):
            result = await citation_service.get_citation(db, "cit-1", "user-1")
        assert result.id == "cit-1"

    async def test_list_citations_success(self, citation_service, db, citation_repo):
        citation_repo.get_by_workspace = AsyncMock(return_value=[_make_citation(), _make_citation(id="cit-2")])

        with patch.object(citation_service, "_verify_workspace_access", AsyncMock()):
            results, total = await citation_service.list_citations(db, "ws-1", "user-1", 0, 10)
        assert total == 2
        assert len(results) == 2

    async def test_export_citations_success(self, citation_service, db, citation_repo):
        cit = _make_citation()
        citation_repo.get = AsyncMock(return_value=cit)

        with patch.object(citation_service, "_verify_workspace_access", AsyncMock()):
            data = CitationExportRequest(citation_ids=["cit-1"], format="bibtex")
            result = await citation_service.export_citations(db, "user-1", data)

        assert result.format == "bibtex"
        assert "@article" in result.content

    async def test_export_citations_empty_ids(self, citation_service, db):
        with patch.object(citation_service, "_verify_workspace_access", AsyncMock()):
            data = CitationExportRequest(citation_ids=[], format="apa")
            result = await citation_service.export_citations(db, "user-1", data)
        assert result.content == ""

    async def test_get_library_summary_success(self, citation_service, db, citation_repo):
        citation_repo.get_by_workspace = AsyncMock(return_value=[_make_citation()])
        citation_repo.count_by_style = AsyncMock(return_value={"apa": 1})
        citation_repo.count_by_source_type = AsyncMock(return_value={"journal": 1})

        with patch.object(citation_service, "_verify_workspace_access", AsyncMock()):
            result = await citation_service.get_library_summary(db, "ws-1", "user-1")
        assert result.total_citations == 1

    def test_generate_citation_bibtex(self, citation_service):
        data = {
            "authors": ["Smith, John", "Doe, Jane"],
            "title": "A Great Paper",
            "year": 2024,
            "journal": "Journal of AI",
            "volume": "10",
            "issue": "2",
            "pages": "1-10",
            "doi": "10.1234/test",
        }
        result = citation_service.generate_citation_text(data, "bibtex")
        assert "@article{" in result
        assert "author = {Smith, John and Doe, Jane}" in result

    def test_generate_citation_ris(self, citation_service):
        data = {"authors": ["Smith, John"], "title": "Test", "year": 2024, "journal": "J", "pages": "1-10", "doi": "10.1"}
        result = citation_service.generate_citation_text(data, "ris")
        assert "TY  - JOUR" in result
        assert "SP  - 1" in result
        assert "EP  - 10" in result

    def test_generate_citation_apa(self, citation_service):
        data = {"authors": ["Smith, J"], "title": "Test", "year": 2024, "journal": "J", "volume": "5", "pages": "10-20"}
        result = citation_service.generate_citation_text(data, "apa")
        assert "Smith, J" in result
        assert "(2024)" in result

    def test_generate_citation_apa_two_authors(self, citation_service):
        data = {"authors": ["Smith, J", "Doe, J"], "title": "Test", "year": 2024}
        result = citation_service.generate_citation_text(data, "apa")
        assert "&" in result

    def test_generate_citation_apa_three_authors(self, citation_service):
        data = {"authors": ["Smith, J", "Doe, J", "Lee, K"], "title": "Test", "year": 2024}
        result = citation_service.generate_citation_text(data, "apa")
        assert "et al." in result

    def test_generate_citation_mla(self, citation_service):
        data = {"authors": ["Smith, John"], "title": "Test", "journal": "J", "volume": "5", "year": 2024, "pages": "10-20"}
        result = citation_service.generate_citation_text(data, "mla")
        assert "Smith, John." in result
        assert '"Test."' in result

    def test_generate_citation_mla_two_authors(self, citation_service):
        data = {"authors": ["Smith, J", "Doe, J"], "title": "Test"}
        result = citation_service.generate_citation_text(data, "mla")
        assert " and " in result

    def test_generate_citation_ieee(self, citation_service):
        data = {"authors": ["Smith, John"], "title": "Test", "journal": "J", "volume": "5", "year": 2024, "pages": "10"}
        result = citation_service.generate_citation_text(data, "ieee")
        assert "J. Smith" in result

    def test_generate_citation_unknown_style(self, citation_service):
        data = {"title": "Just Title"}
        result = citation_service.generate_citation_text(data, "unknown")
        assert result == "Just Title"

    async def test_verify_workspace_access_owner(self, citation_service, db):
        with patch("app.services.citation_service.WorkspaceRepository") as mock_cls:
            mock_ws = AsyncMock()
            mock_ws.get = AsyncMock(return_value=_make_workspace(owner_id="user-1"))
            mock_cls.return_value = mock_ws
            await citation_service._verify_workspace_access(db, "ws-1", "user-1")

    async def test_verify_workspace_access_denied(self, citation_service, db):
        with patch("app.services.citation_service.WorkspaceRepository") as mock_cls:
            mock_ws = AsyncMock()
            mock_ws.get = AsyncMock(return_value=_make_workspace(owner_id="owner-1"))
            mock_ws.get_member_role = AsyncMock(return_value=None)
            mock_cls.return_value = mock_ws
            with pytest.raises(AuthorizationError):
                await citation_service._verify_workspace_access(db, "ws-1", "user-2")


# ---------------------------------------------------------------------------
# LibraryService / PaperService
# ---------------------------------------------------------------------------

@pytest.fixture
def library_service(paper_repo):
    return LibraryService(repo=paper_repo)


@pytest.fixture
def paper_service(paper_repo):
    return PaperService(repo=paper_repo)


class TestLibraryService:
    async def test_upload_paper_success(self, library_service, db, paper_repo):
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=b"content")
        mock_file.filename = "paper.pdf"
        paper = _make_paper()
        paper_repo.create = AsyncMock(return_value=paper)

        with patch("app.services.library_service.WorkspaceRepository") as mock_ws_cls:
            mock_ws = AsyncMock()
            mock_ws.get = AsyncMock(return_value=_make_workspace(owner_id="user-1"))
            mock_ws_cls.return_value = mock_ws
            with patch("app.services.library_service.os.makedirs"):
                with patch("app.services.library_service.open", MagicMock()):
                    result = await library_service.upload_paper(db, "ws-1", "user-1", mock_file)

        assert isinstance(result, PaperUploadResponse)
        assert result.title == "Test Paper"

    async def test_upload_paper_with_metadata(self, library_service, db, paper_repo):
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=b"content")
        mock_file.filename = "paper.pdf"
        paper = _make_paper()
        paper_repo.create = AsyncMock(return_value=paper)
        meta = PaperUpdate(title="Custom Title", doi="10.1", authors=["A"])

        with patch("app.services.library_service.WorkspaceRepository") as mock_ws_cls:
            mock_ws = AsyncMock()
            mock_ws.get = AsyncMock(return_value=_make_workspace())
            mock_ws_cls.return_value = mock_ws
            with patch("app.services.library_service.os.makedirs"):
                with patch("app.services.library_service.open", MagicMock()):
                    result = await library_service.upload_paper(db, "ws-1", "user-1", mock_file, metadata=meta)

        assert result.title == "Test Paper"

    @staticmethod
    def _patch_ws_repo(owner_id="user-1"):
        mock_ws = AsyncMock()
        mock_ws.get = AsyncMock(return_value=_make_workspace(owner_id=owner_id))
        mock_ws.get_member_role = AsyncMock(return_value=None)
        return patch("app.services.library_service.WorkspaceRepository", return_value=mock_ws)

    async def test_delete_paper_success(self, library_service, db, paper_repo):
        from app.services.library_service import STORAGE_DIR
        safe_path = os.path.join(STORAGE_DIR, "test.pdf")
        paper = _make_paper(file_path=safe_path)
        paper_repo.get = AsyncMock(return_value=paper)
        paper_repo.delete = AsyncMock()

        with self._patch_ws_repo():
            with patch("os.path.exists", return_value=True), patch("os.remove") as mock_remove:
                await library_service.delete_paper(db, "paper-1", "user-1")
                mock_remove.assert_called_once_with(safe_path)

        paper_repo.delete.assert_awaited_once_with(db, "paper-1")

    async def test_delete_paper_no_file(self, library_service, db, paper_repo):
        paper = _make_paper(file_path=None)
        paper_repo.get = AsyncMock(return_value=paper)
        paper_repo.delete = AsyncMock()

        with self._patch_ws_repo():
            await library_service.delete_paper(db, "paper-1", "user-1")
        paper_repo.delete.assert_awaited_once_with(db, "paper-1")

    async def test_replace_paper_success(self, library_service, db, paper_repo):
        old_paper = _make_paper(version=1)
        paper_repo.get = AsyncMock(return_value=old_paper)
        new_paper = _make_paper(version=2)
        paper_repo.update = AsyncMock(return_value=new_paper)

        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=b"new content")
        mock_file.filename = "v2.pdf"

        with self._patch_ws_repo():
            with patch("app.services.library_service.os.makedirs"):
                with patch("app.services.library_service.open", MagicMock()):
                    result = await library_service.replace_paper(db, "paper-1", "user-1", mock_file)

        assert result.version == 2

    async def test_update_metadata_success(self, library_service, db, paper_repo):
        paper = _make_paper(title="Old")
        paper_repo.get = AsyncMock(return_value=paper)
        updated = _make_paper(title="New Title")
        paper_repo.update = AsyncMock(return_value=updated)

        data = PaperUpdate(title="New Title")
        with self._patch_ws_repo():
            result = await library_service.update_metadata(db, "paper-1", "user-1", data)
        assert result.title == "New Title"

    async def test_get_paper_success(self, library_service, db, paper_repo):
        paper = _make_paper()
        paper_repo.get = AsyncMock(return_value=paper)
        with self._patch_ws_repo():
            result = await library_service.get_paper(db, "paper-1", "user-1")
        assert isinstance(result, PaperResponse)
        assert result.id == "paper-1"

    async def test_get_paper_forbidden(self, library_service, db, paper_repo):
        paper = _make_paper()
        paper_repo.get = AsyncMock(return_value=paper)
        with self._patch_ws_repo(owner_id="someone-else"):
            with pytest.raises(AuthorizationError):
                await library_service.get_paper(db, "paper-1", "user-1")

    async def test_list_papers_success(self, library_service, db, paper_repo):
        paper_repo.get_by_workspace = AsyncMock(return_value=[_make_paper(), _make_paper(id="p2")])
        paper_repo.count = AsyncMock(return_value=2)
        with self._patch_ws_repo():
            results, total = await library_service.list_papers(db, "ws-1", "user-1", 0, 10)
        assert total == 2
        assert len(results) == 2

    async def test_list_papers_with_status(self, library_service, db, paper_repo):
        paper_repo.get_by_workspace = AsyncMock(return_value=[_make_paper()])
        paper_repo.count = AsyncMock(return_value=1)
        with self._patch_ws_repo():
            results, total = await library_service.list_papers(db, "ws-1", "user-1", 0, 10, status="active")
        assert total == 1

    async def test_check_duplicate_by_hash(self, library_service, db, paper_repo):
        paper_repo.find_by_content_hash = AsyncMock(return_value=_make_paper())
        with self._patch_ws_repo():
            result = await library_service.check_duplicate(db, "ws-1", "user-1", content_hash="abc123")
        assert result.is_duplicate is True
        assert result.confidence == 1.0

    async def test_check_duplicate_by_doi(self, library_service, db, paper_repo):
        paper_repo.find_by_content_hash = AsyncMock(return_value=None)
        paper_repo.find_by_doi = AsyncMock(return_value=_make_paper())
        with self._patch_ws_repo():
            result = await library_service.check_duplicate(db, "ws-1", "user-1", doi="10.1234/test")
        assert result.is_duplicate is True
        assert result.confidence == 0.9

    async def test_check_duplicate_none(self, library_service, db, paper_repo):
        paper_repo.find_by_content_hash = AsyncMock(return_value=None)
        with self._patch_ws_repo():
            result = await library_service.check_duplicate(db, "ws-1", "user-1")
        assert result.is_duplicate is False
        assert result.confidence == 0.0

    async def test_get_versions_success(self, library_service, db, paper_repo):
        paper = _make_paper(version=3)
        paper_repo.get = AsyncMock(return_value=paper)
        with self._patch_ws_repo():
            versions = await library_service.get_versions(db, "paper-1", "user-1")
        assert len(versions) == 3
        for v in versions:
            assert isinstance(v, PaperVersionResponse)


class TestPaperService:
    # PaperService is an alias for LibraryService; test a simple method
    async def test_paper_service_alias(self, paper_service, db, paper_repo):
        paper = _make_paper()
        paper_repo.get = AsyncMock(return_value=paper)
        mock_ws = AsyncMock()
        mock_ws.get = AsyncMock(return_value=_make_workspace(owner_id="user-1"))
        with patch("app.services.library_service.WorkspaceRepository", return_value=mock_ws):
            result = await paper_service.get_paper(db, "paper-1", "user-1")
        assert isinstance(result, PaperResponse)


# ---------------------------------------------------------------------------
# DashboardService
# ---------------------------------------------------------------------------

@pytest.fixture
def dashboard_service(
    event_manager, session_repo, project_repo, ws_repo, paper_repo,
    citation_repo, conversation_repo,
):
    return DashboardService(
        event_manager=event_manager,
        session_repo=session_repo,
        project_repo=project_repo,
        workspace_repo=ws_repo,
        paper_repo=paper_repo,
        citation_repo=citation_repo,
        conversation_repo=conversation_repo,
    )


def _grant_workflow_access(session_repo, project_repo, ws_repo, workflow_id="wf-1", user_id="user-1"):
    session_repo.get_by_workflow_id = AsyncMock(return_value=_make_session(workflow_id=workflow_id))
    project_repo.get = AsyncMock(return_value=_make_project())
    ws_repo.get = AsyncMock(return_value=_make_workspace(owner_id=user_id))


class TestDashboardService:
    async def test_get_workflow_status_running(
        self, dashboard_service, event_manager, db, session_repo, project_repo, ws_repo
    ):
        _grant_workflow_access(session_repo, project_repo, ws_repo)
        session_repo.get_by_workflow_id = AsyncMock(
            return_value=_make_session(
                workflow_id="wf-1", status="running", completed_at=None,
            )
        )

        from app.streaming.events import EventType
        started_event = MagicMock()
        started_event.type = EventType.AGENT_STARTED
        started_event.agent_id = "Analysis"
        event_manager.get_event_history = AsyncMock(return_value=[started_event])

        result = await dashboard_service.get_workflow_status(db, "wf-1", "user-1")
        assert isinstance(result, WorkflowStatusResponse)
        assert result.status == "running"
        assert result.current_phase == "Analysis"

    async def test_get_workflow_status_completed(
        self, dashboard_service, event_manager, db, session_repo, project_repo, ws_repo
    ):
        _grant_workflow_access(session_repo, project_repo, ws_repo)
        session_repo.get_by_workflow_id = AsyncMock(
            return_value=_make_session(workflow_id="wf-1", status="completed")
        )

        from app.streaming.events import EventType
        completed_event = MagicMock()
        completed_event.type = EventType.WORKFLOW_COMPLETED
        completed_event.timestamp = datetime.datetime.now(datetime.UTC)
        event_manager.get_event_history = AsyncMock(return_value=[completed_event])

        result = await dashboard_service.get_workflow_status(db, "wf-1", "user-1")
        assert result.completed_at is not None
        assert result.progress_pct == 100.0

    async def test_get_workflow_status_no_state(
        self, dashboard_service, event_manager, db, session_repo, project_repo, ws_repo
    ):
        _grant_workflow_access(session_repo, project_repo, ws_repo)
        session_repo.get_by_workflow_id = AsyncMock(
            return_value=_make_session(
                workflow_id="wf-1", status="pending", started_at=None, completed_at=None,
            )
        )
        event_manager.get_event_history = AsyncMock(return_value=[])

        result = await dashboard_service.get_workflow_status(db, "wf-1", "user-1")
        assert result.status == "pending"

    async def test_get_workflow_status_not_found(self, dashboard_service, db, session_repo):
        session_repo.get_by_workflow_id = AsyncMock(return_value=None)
        with pytest.raises(NotFoundError):
            await dashboard_service.get_workflow_status(db, "wf-missing", "user-1")

    async def test_get_workflow_status_forbidden(self, dashboard_service, db, session_repo, project_repo, ws_repo):
        _grant_workflow_access(session_repo, project_repo, ws_repo, user_id="someone-else")
        ws_repo.get_member_role = AsyncMock(return_value=None)
        with pytest.raises(AuthorizationError):
            await dashboard_service.get_workflow_status(db, "wf-1", "user-1")

    async def test_get_token_usage_success(self, dashboard_service, event_manager, db, session_repo, project_repo, ws_repo):
        _grant_workflow_access(session_repo, project_repo, ws_repo)
        event = MagicMock()
        event.data = {
            "token_usage": {
                "total_tokens": 500,
                "prompt_tokens": 200,
                "completion_tokens": 300,
                "cost": 0.02,
            }
        }
        event_manager.get_event_history = AsyncMock(return_value=[event])

        result = await dashboard_service.get_token_usage(db, "wf-1", "user-1")
        assert isinstance(result, TokenUsageResponse)
        assert result.total_tokens == 500
        assert result.prompt_tokens == 200
        assert result.completion_tokens == 300

    async def test_get_token_usage_empty(self, dashboard_service, event_manager, db, session_repo, project_repo, ws_repo):
        _grant_workflow_access(session_repo, project_repo, ws_repo)
        event = MagicMock()
        event.data = {}
        event_manager.get_event_history = AsyncMock(return_value=[event])

        result = await dashboard_service.get_token_usage(db, "wf-1", "user-1")
        assert result.total_tokens == 0

    async def test_get_provider_usage_success(self, dashboard_service, event_manager, db, session_repo, project_repo, ws_repo):
        _grant_workflow_access(session_repo, project_repo, ws_repo)
        event = MagicMock()
        event.data = {
            "provider_call": {
                "provider": "openai",
                "model": "gpt-4",
                "tokens": 100,
                "cost": 0.01,
            }
        }
        event_manager.get_event_history = AsyncMock(return_value=[event, event])

        result = await dashboard_service.get_provider_usage(db, "wf-1", "user-1")
        assert len(result) == 1
        assert result[0].calls == 2

    async def test_get_provider_usage_empty(self, dashboard_service, event_manager, db, session_repo, project_repo, ws_repo):
        _grant_workflow_access(session_repo, project_repo, ws_repo)
        event = MagicMock()
        event.data = {}
        event_manager.get_event_history = AsyncMock(return_value=[event])

        result = await dashboard_service.get_provider_usage(db, "wf-1", "user-1")
        assert result == []

    async def test_get_evaluation_scores_success(self, dashboard_service, event_manager, db, session_repo, project_repo, ws_repo):
        _grant_workflow_access(session_repo, project_repo, ws_repo)
        event = MagicMock()
        event.data = {
            "evaluation": {
                "metric": "accuracy",
                "score": 0.95,
                "details": {"correct": 19, "total": 20},
            }
        }
        event_manager.get_event_history = AsyncMock(return_value=[event])

        result = await dashboard_service.get_evaluation_scores(db, "wf-1", "user-1")
        assert len(result) == 1
        assert result[0].metric == "accuracy"

    async def test_get_evaluation_scores_empty(self, dashboard_service, event_manager, db, session_repo, project_repo, ws_repo):
        _grant_workflow_access(session_repo, project_repo, ws_repo)
        event = MagicMock()
        event.data = {}
        event_manager.get_event_history = AsyncMock(return_value=[event])

        result = await dashboard_service.get_evaluation_scores(db, "wf-1", "user-1")
        assert result == []

    async def test_get_dashboard_success(self, dashboard_service, event_manager, db, session_repo, project_repo, ws_repo):
        _grant_workflow_access(session_repo, project_repo, ws_repo)
        event_manager.get_event_history = AsyncMock(return_value=[])

        result = await dashboard_service.get_full_dashboard(db, "wf-1", "user-1")
        assert isinstance(result, DashboardResponse)

    async def test_get_workflow_timeline(self, dashboard_service, event_manager, db, session_repo, project_repo, ws_repo):
        _grant_workflow_access(session_repo, project_repo, ws_repo)
        event = MagicMock()
        event.event_id = "e1"
        event.type = MagicMock()
        event.type.value = "agent_started"
        event.timestamp = datetime.datetime.now(datetime.UTC)
        event.data = {}
        event_manager.get_event_history = AsyncMock(return_value=[event])

        timeline = await dashboard_service.get_event_timeline(db, "wf-1", "user-1")
        assert len(timeline) == 1
        assert timeline[0]["event_id"] == "e1"


# ---------------------------------------------------------------------------
# DocumentService
# ---------------------------------------------------------------------------

@pytest.fixture
def document_service(document_repo, writing_agent):
    return DocumentService(repo=document_repo, writing_agent=writing_agent)


class TestDocumentService:
    async def test_generate_document_success(self, document_service, db, document_repo, writing_agent):
        agent_output = MagicMock()
        agent_output.output = {"sections": [{"heading": "Intro", "content": "Hello."}], "citations": []}
        writing_agent.execute = AsyncMock(return_value=agent_output)
        doc = _make_document()
        document_repo.create = AsyncMock(return_value=doc)

        with patch("app.services.document_service.WorkspaceRepository") as mock_ws_cls:
            mock_ws = AsyncMock()
            mock_ws.get = AsyncMock(return_value=_make_workspace())
            mock_ws_cls.return_value = mock_ws
            with patch("app.services.document_service.os.makedirs"):
                with patch("app.services.document_service.open", MagicMock()):
                    data = DocumentGenerateRequest(
                        workspace_id="ws-1", format="markdown", title="My Doc"
                    )
                    result = await document_service.generate_document(db, "user-1", data)

        assert isinstance(result, DocumentResponse)
        assert result.title == "Test Doc"

    async def test_get_document_success(self, document_service, db, document_repo):
        doc = _make_document()
        document_repo.get = AsyncMock(return_value=doc)
        result = await document_service.get_document(db, "doc-1", "user-1")
        assert result.id == "doc-1"

    async def test_get_document_not_found(self, document_service, db, document_repo):
        document_repo.get = AsyncMock(side_effect=NotFoundError("Document", "bad"))
        with pytest.raises(NotFoundError):
            await document_service.get_document(db, "bad", "user-1")

    async def test_list_documents_success(self, document_service, db, document_repo):
        document_repo.get_by_workspace = AsyncMock(return_value=[_make_document(), _make_document(id="d2")])
        results, total = await document_service.list_documents(db, "ws-1", "user-1", 0, 10)
        assert total == 2
        assert len(results) == 2

    async def test_export_document_markdown(self, document_service, db, document_repo):
        doc = _make_document(content="# Title\n\nContent.", format="markdown")
        document_repo.get = AsyncMock(return_value=doc)

        result = await document_service.export_document(db, "doc-1", "user-1", "markdown")
        assert isinstance(result, DocumentExportResponse)
        assert result.format == "markdown"

    async def test_export_document_html(self, document_service, db, document_repo):
        doc = _make_document(content="# Title\n\nHello.", format="markdown")
        document_repo.get = AsyncMock(return_value=doc)

        result = await document_service.export_document(db, "doc-1", "user-1", "html")
        assert "<h1>Title</h1>" in result.content

    async def test_export_document_pdf(self, document_service, db, document_repo):
        doc = _make_document(content="# Title", format="markdown")
        document_repo.get = AsyncMock(return_value=doc)

        result = await document_service.export_document(db, "doc-1", "user-1", "pdf")
        assert "<h1>Title</h1>" in result.content

    def test_sections_to_markdown(self, document_service):
        sections = [
            {"heading": "Intro", "content": "Text."},
            {"heading": "Conclusion", "content": "End."},
        ]
        result = document_service._sections_to_markdown(sections, "Title")
        assert result.startswith("# Title")
        assert "## Intro" in result
        assert "## Conclusion" in result

    def test_format_content_markdown(self, document_service):
        assert document_service._format_content("# hi", "markdown", "T") == "# hi"

    def test_format_content_html(self, document_service):
        result = document_service._format_content("# Title\n\nPara", "html", "T")
        assert "<h1>Title</h1>" in result
        assert "<p>Para</p>" in result

    def test_format_extension(self, document_service):
        assert document_service._format_extension("markdown") == ".md"
        assert document_service._format_extension("html") == ".html"
        assert document_service._format_extension("pdf") == ".pdf"
        assert document_service._format_extension("docx") == ".docx"
        from app.core.exceptions import AARAError
        with pytest.raises(AARAError):
            document_service._format_extension("other")


# ---------------------------------------------------------------------------
# SearchService
# ---------------------------------------------------------------------------

@pytest.fixture
def search_service(paper_repo, citation_repo, project_repo, vector_search):
    return SearchService(
        paper_repo=paper_repo,
        citation_repo=citation_repo,
        project_repo=project_repo,
        vector_search=vector_search,
    )


class TestSearchService:
    async def test_search_papers_success(self, search_service, db, paper_repo):
        paper = _make_paper(title="ML Paper", abstract="About ML")
        paper_repo.search = AsyncMock(return_value=[paper])

        data = SearchRequest(query="ML", scope="papers", workspace_id="ws-1")
        result = await search_service.search(db, "user-1", data)

        assert len(result.results) == 1
        assert result.results[0].type == "paper"

    async def test_search_papers_no_workspace(self, search_service, db):
        data = SearchRequest(query="ML", scope="papers")
        result = await search_service.search(db, "user-1", data)
        assert result.total == 0

    async def test_search_citations_success(self, search_service, db, citation_repo):
        cit = _make_citation(title="Citation Title")
        citation_repo.search = AsyncMock(return_value=[cit])

        data = SearchRequest(query="title", scope="citations", workspace_id="ws-1")
        result = await search_service.search(db, "user-1", data)

        assert len(result.results) == 1
        assert result.results[0].type == "citation"

    async def test_search_citations_no_workspace(self, search_service, db):
        data = SearchRequest(query="title", scope="citations")
        result = await search_service.search(db, "user-1", data)
        assert result.total == 0

    async def test_search_projects_success(self, search_service, db, project_repo):
        proj = _make_project(name="AI Research", description="About AI")
        project_repo.get_by_workspace = AsyncMock(return_value=[proj])

        data = SearchRequest(query="AI", scope="projects", workspace_id="ws-1")
        result = await search_service.search(db, "user-1", data)

        assert len(result.results) == 1
        assert result.results[0].type == "project"

    async def test_search_projects_no_match(self, search_service, db, project_repo):
        proj = _make_project(name="Other", description="Nothing")
        project_repo.get_by_workspace = AsyncMock(return_value=[proj])

        data = SearchRequest(query="AI", scope="projects", workspace_id="ws-1")
        result = await search_service.search(db, "user-1", data)
        assert result.total == 0

    async def test_search_projects_no_workspace(self, search_service, db):
        data = SearchRequest(query="AI", scope="projects")
        result = await search_service.search(db, "user-1", data)
        assert result.total == 0

    async def test_search_workspaces_success(self, search_service, db):
        ws = _make_workspace(name="ML Workspace", description="ML experiments")

        with patch.object(search_service, "_search_workspaces") as mock_fn:
            mock_fn.return_value = (
                [SearchResult(id=ws.id, type="workspace", title=ws.name, snippet=ws.description or "", score=1.0)],
                1,
            )
            data = SearchRequest(query="ML", scope="workspace", workspace_id="ws-1")
            result = await search_service.search(db, "user-1", data)
        assert len(result.results) == 1

    async def test_search_workspaces_with_ws_repo(self, search_service, db):
        ws = _make_workspace(name="ML Workspace", description="ML experiments")
        with patch("app.services.search_service.WorkspaceRepository") as mock_cls:
            mock_repo = AsyncMock()
            mock_repo.get_for_user = AsyncMock(return_value=[ws])
            mock_cls.return_value = mock_repo

            data = SearchRequest(query="ML", scope="workspace", workspace_id="ws-1")
            result = await search_service.search(db, "user-1", data)
        assert len(result.results) == 1

    async def test_search_workspaces_no_match(self, search_service, db):
        ws = _make_workspace(name="Other", description="Other")
        with patch("app.services.search_service.WorkspaceRepository") as mock_cls:
            mock_repo = AsyncMock()
            mock_repo.get_for_user = AsyncMock(return_value=[ws])
            mock_cls.return_value = mock_repo

            data = SearchRequest(query="ML", scope="workspace", workspace_id="ws-1")
            result = await search_service.search(db, "user-1", data)
        assert result.total == 0

    async def test_search_semantic_no_vector_search(self, search_service, db):
        search_service._vector_search = None
        data = SearchRequest(query="AI", scope="semantic", workspace_id="ws-1")
        result = await search_service.search(db, "user-1", data)
        assert result.total == 0

    async def test_search_semantic_no_workspace(self, search_service, db):
        data = SearchRequest(query="AI", scope="semantic")
        result = await search_service.search(db, "user-1", data)
        assert result.total == 0

    async def test_search_semantic_success(self, search_service, db, vector_search):
        vector_search.search = AsyncMock(
            return_value=[
                {"id": "p1", "title": "Paper 1", "snippet": "About AI", "score": 0.95, "metadata": {}}
            ]
        )
        data = SearchRequest(query="AI", scope="semantic", workspace_id="ws-1")
        result = await search_service.search(db, "user-1", data)
        assert len(result.results) == 1
        assert result.results[0].score == 0.95

    async def test_search_semantic_exception(self, search_service, db, vector_search):
        vector_search.search = AsyncMock(side_effect=Exception("fail"))
        data = SearchRequest(query="AI", scope="semantic", workspace_id="ws-1")
        result = await search_service.search(db, "user-1", data)
        assert result.total == 0

    async def test_search_unknown_scope(self, search_service, db):
        data = SearchRequest(query="AI", scope="workspace")
        search_service._search_workspaces = AsyncMock(return_value=([], 0))
        result = await search_service.search(db, "user-1", data)
        assert result.total == 0

    async def test_search_pagination(self, search_service, db, paper_repo):
        paper_repo.search = AsyncMock(return_value=[_make_paper()])
        data = SearchRequest(query="ML", scope="papers", workspace_id="ws-1", page=2, page_size=5)
        result = await search_service.search(db, "user-1", data)
        assert result.page == 2
        assert result.page_size == 5
        assert result.total_pages >= 1


# ---------------------------------------------------------------------------
# Additional edge-case tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    async def test_workspace_service_get_not_found(self, workspace_service, db, ws_repo):
        ws_repo.get = AsyncMock(side_effect=NotFoundError("Workspace", "bad"))
        with pytest.raises(NotFoundError):
            await workspace_service.get_workspace(db, "bad", "user-1")

    async def test_project_service_get_not_found(self, project_service, db, project_repo):
        project_repo.get = AsyncMock(side_effect=NotFoundError("ResearchProject", "bad"))
        with pytest.raises(NotFoundError):
            await project_service.get_project(db, "bad", "user-1")

    async def test_citation_service_get_not_found(self, citation_service, db, citation_repo):
        citation_repo.get = AsyncMock(side_effect=NotFoundError("Citation", "bad"))
        with pytest.raises(NotFoundError):
            await citation_service.get_citation(db, "bad", "user-1")

    async def test_library_service_get_not_found(self, library_service, db, paper_repo):
        paper_repo.get = AsyncMock(side_effect=NotFoundError("ResearchPaper", "bad"))
        with pytest.raises(NotFoundError):
            await library_service.get_paper(db, "bad", "user-1")

    async def test_document_service_export_not_found(self, document_service, db, document_repo):
        document_repo.get = AsyncMock(side_effect=NotFoundError("Document", "bad"))
        with pytest.raises(NotFoundError):
            await document_service.export_document(db, "bad", "user-1", "markdown")

    async def test_research_service_list_sessions_no_project(self, research_service, db, project_repo):
        project_repo.get = AsyncMock(side_effect=NotFoundError("ResearchProject", "bad"))
        with pytest.raises(NotFoundError):
            await research_service.list_sessions(db, "bad", "user-1", 0, 10)

    def test_citation_format_authors_apa_empty(self, citation_service):
        assert citation_service._format_authors_apa([]) == ""

    def test_citation_format_authors_mla_empty(self, citation_service):
        assert citation_service._format_authors_mla([]) == ""

    def test_citation_format_authors_ieee_empty(self, citation_service):
        assert citation_service._format_authors_ieee([]) == ""

    def test_citation_format_authors_ieee_no_comma(self, citation_service):
        result = citation_service._format_authors_ieee(["Smith, John"])
        assert "J. Smith" in result

    def test_citation_generate_apa_no_journal(self, citation_service):
        data = {"authors": ["Smith, J"], "title": "Test", "year": 2024}
        result = citation_service.generate_citation_text(data, "apa")
        assert "Test" in result

    def test_document_markdown_to_html(self, document_service):
        result = document_service._markdown_to_html("# Title\n\n## Sub\n\nPara", "Title")
        assert "<h1>Title</h1>" in result
        assert "<h2>Sub</h2>" in result
        assert "<p>Para</p>" in result
