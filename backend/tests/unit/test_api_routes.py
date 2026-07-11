from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.services
import app.services.citation_service
import app.services.dashboard_service
import app.services.document_service
import app.services.library_service
import app.services.paper_service
import app.services.project_service
import app.services.research_service
import app.services.search_service
import app.services.workspace_service
from app.api.routes.citations import router as citations_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.documents import router as documents_router
from app.api.routes.library import router as library_router
from app.api.routes.projects import router as projects_router
from app.api.routes.quality_checks import router as quality_checks_router
from app.api.routes.research import router as research_router
from app.api.routes.search import router as search_router
from app.api.routes.workspaces import router as workspaces_router
from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.schemas.auth import UserResponse


def _mock_workspace(**kwargs: Any) -> dict:
    defaults = {
        "id": "ws-1",
        "name": "Test Workspace",
        "description": "A test workspace",
        "research_topic": "AI",
        "status": "active",
        "owner_id": "user-1",
        "member_count": 1,
        "paper_count": 0,
        "workflow_count": 0,
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
    }
    return {**defaults, **kwargs}


def _mock_project(**kwargs: Any) -> dict:
    defaults = {
        "id": "proj-1",
        "workspace_id": "ws-1",
        "name": "Test Project",
        "description": "A test project",
        "status": "active",
        "research_goal": "Learn AI",
        "key_questions": [],
        "session_count": 2,
        "paper_count": 5,
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
    }
    return {**defaults, **kwargs}


def _mock_session(**kwargs: Any) -> dict:
    defaults = {
        "id": "sess-1",
        "project_id": "proj-1",
        "status": "completed",
        "workflow_id": "wf-1",
        "query": "test query",
        "agent_phases_completed": 0,
        "total_tokens": 100,
        "total_cost": 0.05,
        "started_at": "2025-01-01T00:00:00",
        "completed_at": "2025-01-01T00:00:00",
        "error_message": None,
        "created_at": "2025-01-01T00:00:00",
    }
    return {**defaults, **kwargs}


def _mock_citation(**kwargs: Any) -> dict:
    defaults = {
        "id": "cit-1",
        "workspace_id": "ws-1",
        "paper_id": None,
        "raw_citation_text": "",
        "formatted_citation": "",
        "style": "apa",
        "source_type": "journal",
        "authors": ["Author A"],
        "title": "Test Paper",
        "year": 2025,
        "journal": "Test Journal",
        "volume": "1",
        "issue": "1",
        "pages": "1-10",
        "doi": "10.1234/test",
        "url": "https://example.com",
        "isbn": None,
        "publisher": "Test Publisher",
        "accessed_date": None,
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
    }
    return {**defaults, **kwargs}


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_current_user():
    return UserResponse(
        id="user-1",
        email="test@example.com",
        display_name="Test User",
        role="researcher",
        is_active=True,
        created_at=datetime(2025, 1, 1),
    )


@pytest.fixture
def app(mock_db, mock_current_user):
    from app.core.middleware import AARAErrorMiddleware

    application = FastAPI()
    application.add_middleware(AARAErrorMiddleware)
    application.include_router(workspaces_router)
    application.include_router(projects_router)
    application.include_router(research_router)
    application.include_router(citations_router)
    application.include_router(library_router)
    application.include_router(documents_router)
    application.include_router(dashboard_router)
    application.include_router(search_router)
    application.include_router(quality_checks_router)
    application.dependency_overrides[get_db] = lambda: mock_db
    application.dependency_overrides[get_current_active_user] = lambda: mock_current_user
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def mock_workspace_service():
    with patch("app.services.workspace_service.WorkspaceService") as m:
        instance = m.return_value
        ws = _mock_workspace()
        instance.list_workspaces = AsyncMock(return_value=([ws], 1))
        instance.create_workspace = AsyncMock(return_value=ws)
        instance.get_workspace = AsyncMock(return_value=ws)
        instance.update_workspace = AsyncMock(return_value=ws)
        instance.delete_workspace = AsyncMock()
        instance.add_member = AsyncMock()
        instance.remove_member = AsyncMock()
        yield instance


@pytest.fixture
def mock_project_service():
    with patch("app.services.project_service.ProjectService") as m:
        instance = m.return_value
        proj = _mock_project()
        instance.list_projects = AsyncMock(return_value=([proj], 1))
        instance.create_project = AsyncMock(return_value=proj)
        instance.get_project = AsyncMock(return_value=proj)
        instance.update_project = AsyncMock(return_value=proj)
        instance.delete_project = AsyncMock()
        instance.archive_project = AsyncMock(return_value=proj)
        instance.duplicate_project = AsyncMock(return_value=proj)
        yield instance


@pytest.fixture
def mock_research_service():
    with patch("app.services.research_service.ResearchService") as m:
        instance = m.return_value
        sess = _mock_session()
        instance.submit_query = AsyncMock(return_value={"session_id": "sess-1", "workflow_id": "wf-1", "status": "completed", "message": "ok"})
        instance.list_sessions = AsyncMock(return_value=([sess], 1))
        instance.get_session = AsyncMock(return_value=sess)
        instance.trigger_retrieval = AsyncMock(return_value=sess)
        instance.trigger_analysis = AsyncMock(return_value=sess)
        instance.trigger_writing = AsyncMock(return_value=sess)
        instance.upload_pdf = AsyncMock(return_value={"id": "paper-1", "title": "paper", "file_type": "pdf", "file_size": 100, "status": "active", "version": 1, "created_at": "2025-01-01"})
        instance.upload_paper = AsyncMock(return_value={"id": "paper-1", "title": "paper", "file_type": "pdf", "file_size": 100, "status": "active", "version": 1, "created_at": "2025-01-01"})
        instance.get_overview = AsyncMock(return_value={
            "projects": 2, "papers": 5, "notes": 0, "ideas": 0,
            "activeProjects": 1, "completedProjects": 1, "inProgressProjects": 1, "staleProjects": 0,
        })
        instance.get_activity = AsyncMock(return_value={"recentlyOpened": []})
        instance.get_cards = AsyncMock(return_value=[])
        instance.get_recent_activity = AsyncMock(return_value=[])
        instance.get_notes = AsyncMock(return_value=[])
        instance.get_reading_queue = AsyncMock(return_value=[])
        instance.get_saved_papers = AsyncMock(return_value=[])
        yield instance


@pytest.fixture
def mock_citation_service():
    with patch("app.services.citation_service.CitationService") as m:
        instance = m.return_value
        cit = _mock_citation()
        instance.list_citations = AsyncMock(return_value=([cit], 1))
        instance.create_citation = AsyncMock(return_value=cit)
        instance.get_citation = AsyncMock(return_value=cit)
        instance.update_citation = AsyncMock(return_value=cit)
        instance.delete_citation = AsyncMock()
        instance.export_citations = AsyncMock(return_value={"format": "bibtex", "content": "@article{...}", "filename": "citations.bib"})
        instance.get_library_summary = AsyncMock(return_value={"total_citations": 10, "by_style": {"apa": 5}, "by_source_type": {"journal": 10}})
        yield instance


@pytest.fixture
def mock_paper_service():
    with patch("app.services.paper_service.PaperService") as m:
        instance = m.return_value
        instance.list_papers = AsyncMock(return_value=([], 0))
        instance.upload_paper = AsyncMock(return_value=_mock_workspace(name="Paper Title"))
        instance.get_paper = AsyncMock(return_value=_mock_workspace(name="Paper Title"))
        instance.update_paper = AsyncMock(return_value=_mock_workspace(name="Updated Paper"))
        instance.delete_paper = AsyncMock()
        instance.replace_paper = AsyncMock(return_value=_mock_workspace(name="Replaced Paper"))
        instance.get_paper_versions = AsyncMock(return_value=[])
        instance.check_duplicate = AsyncMock(return_value={"is_duplicate": False, "existing_paper": None, "confidence": 0.0})
        yield instance


@pytest.fixture
def mock_document_service():
    with patch("app.services.document_service.DocumentService") as m:
        instance = m.return_value
        doc = {"id": "doc-1", "workspace_id": "ws-1", "session_id": None, "format": "markdown", "title": "Test Doc", "content": "# Test", "file_path": None, "file_size": 100, "status": "draft", "version": 1, "citation_count": 0, "template_used": None, "created_at": "2025-01-01", "updated_at": "2025-01-01"}
        instance.generate_document = AsyncMock(return_value=doc)
        instance.list_documents = AsyncMock(return_value=([doc], 1))
        instance.get_document = AsyncMock(return_value=doc)
        instance.export_document = AsyncMock(return_value={"format": "markdown", "content": "# Test", "filename": "test.md", "mime_type": "text/markdown"})
        yield instance


@pytest.fixture
def mock_dashboard_service():
    with patch("app.services.dashboard_service.DashboardService") as m:
        instance = m.return_value
        instance.get_full_dashboard = AsyncMock(return_value={"workflow": {"workflow_id": "wf-1", "status": "completed", "current_phase": None, "current_agent": None, "progress_pct": 100.0, "started_at": None, "completed_at": None, "elapsed_seconds": 10.0}, "tokens": {"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50, "estimated_cost": 0.05}, "providers": [], "evaluation_scores": [], "timeline": []})
        instance.get_workflow_status = AsyncMock(return_value={"workflow_id": "wf-1", "status": "running", "current_phase": "research", "current_agent": "research", "progress_pct": 50.0, "started_at": None, "completed_at": None, "elapsed_seconds": 5.0})
        instance.get_token_usage = AsyncMock(return_value={"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50, "estimated_cost": 0.05})
        instance.get_provider_usage = AsyncMock(return_value=[])
        instance.get_evaluation_scores = AsyncMock(return_value=[])
        instance.get_event_timeline = AsyncMock(return_value=[])
        yield instance


@pytest.fixture
def mock_search_service():
    with patch("app.services.search_service.SearchService") as m:
        instance = m.return_value
        instance.search = AsyncMock(return_value=([], 0))
        yield instance


class TestWorkspacesRoutes:
    def test_list_workspaces_success(self, client, mock_workspace_service):
        mock_workspace_service.list_workspaces.return_value = ([], 0)
        resp = client.get("/api/v1/workspaces")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_workspaces_with_pagination(self, client, mock_workspace_service):
        mock_workspace_service.list_workspaces.return_value = ([], 0)
        resp = client.get("/api/v1/workspaces?page=2&page_size=10")
        assert resp.status_code == 200
        assert resp.json()["page"] == 2

    def test_create_workspace_success(self, client, mock_workspace_service):
        mock_workspace_service.create_workspace.return_value = _mock_workspace(
            id="ws-1",
            name="Test Workspace",
            description="desc",
            research_topic=None,
            status="active",
            owner_id="user-1",
            member_count=1,
            paper_count=0,
            workflow_count=0,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )
        resp = client.post("/api/v1/workspaces", json={"name": "Test Workspace"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "Test Workspace"

    def test_create_workspace_validation_error(self, client):
        resp = client.post("/api/v1/workspaces", json={})
        assert resp.status_code == 422

    def test_get_workspace_success(self, client, mock_workspace_service):
        mock_workspace_service.get_workspace.return_value = _mock_workspace(
            id="ws-1",
            name="Test",
            description=None,
            research_topic=None,
            status="active",
            owner_id="user-1",
            member_count=1,
            paper_count=0,
            workflow_count=0,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )
        resp = client.get("/api/v1/workspaces/ws-1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "ws-1"

    def test_get_workspace_not_found(self, client, mock_workspace_service):
        mock_workspace_service.get_workspace.return_value = None
        resp = client.get("/api/v1/workspaces/ws-none")
        assert resp.status_code == 404

    def test_update_workspace_success(self, client, mock_workspace_service):
        mock_workspace_service.update_workspace.return_value = _mock_workspace(
            id="ws-1",
            name="Updated",
            description=None,
            research_topic=None,
            status="active",
            owner_id="user-1",
            member_count=1,
            paper_count=0,
            workflow_count=0,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )
        resp = client.patch("/api/v1/workspaces/ws-1", json={"name": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_update_workspace_not_found(self, client, mock_workspace_service):
        mock_workspace_service.update_workspace.return_value = None
        resp = client.patch("/api/v1/workspaces/ws-none", json={"name": "Nope"})
        assert resp.status_code == 404

    def test_delete_workspace_success(self, client, mock_workspace_service):
        mock_workspace_service.delete_workspace = AsyncMock()
        resp = client.delete("/api/v1/workspaces/ws-1")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Workspace deleted"

    def test_add_member_success(self, client, mock_workspace_service):
        resp = client.post("/api/v1/workspaces/ws-1/members", json={"user_id": "user-2", "role": "editor"})
        assert resp.status_code == 201
        assert resp.json()["message"] == "Member added"

    def test_remove_member_success(self, client, mock_workspace_service):
        resp = client.delete("/api/v1/workspaces/ws-1/members/user-2")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Member removed"


class TestProjectsRoutes:
    def test_list_projects_success(self, client, mock_project_service):
        mock_project_service.list_projects.return_value = ([], 0)
        resp = client.get("/api/v1/projects?workspace_id=ws-1")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_list_projects_missing_workspace_id(self, client, mock_project_service):
        resp = client.get("/api/v1/projects")
        assert resp.status_code == 422

    def test_list_projects_filter_by_workspace(self, client, mock_project_service):
        mock_project_service.list_projects.return_value = ([], 0)
        resp = client.get("/api/v1/projects?workspace_id=ws-1")
        assert resp.status_code == 200

    def test_create_project_success(self, client, mock_project_service):
        mock_project_service.create_project.return_value = _mock_workspace(
            id="proj-1",
            workspace_id="ws-1",
            name="Test Project",
            description=None,
            status="active",
            research_goal=None,
            key_questions=None,
            session_count=0,
            paper_count=0,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )
        resp = client.post("/api/v1/projects", json={"workspace_id": "ws-1", "name": "Test Project"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "Test Project"

    def test_create_project_validation_error(self, client):
        resp = client.post("/api/v1/projects", json={})
        assert resp.status_code == 422

    def test_get_project_success(self, client, mock_project_service):
        mock_project_service.get_project.return_value = _mock_workspace(
            id="proj-1",
            workspace_id="ws-1",
            name="Test",
            description=None,
            status="active",
            research_goal=None,
            key_questions=None,
            session_count=0,
            paper_count=0,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )
        resp = client.get("/api/v1/projects/proj-1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "proj-1"

    def test_get_project_not_found(self, client, mock_project_service):
        mock_project_service.get_project.side_effect = NotFoundError("ResearchProject", "proj-none")
        resp = client.get("/api/v1/projects/proj-none")
        assert resp.status_code == 404

    def test_update_project_success(self, client, mock_project_service):
        mock_project_service.update_project.return_value = _mock_workspace(
            id="proj-1",
            workspace_id="ws-1",
            name="Updated",
            description=None,
            status="active",
            research_goal=None,
            key_questions=None,
            session_count=0,
            paper_count=0,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )
        resp = client.patch("/api/v1/projects/proj-1", json={"name": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_update_project_not_found(self, client, mock_project_service):
        mock_project_service.update_project.side_effect = NotFoundError("ResearchProject", "proj-none")
        resp = client.patch("/api/v1/projects/proj-none", json={"name": "Nope"})
        assert resp.status_code == 404

    def test_delete_project_success(self, client, mock_project_service):
        resp = client.delete("/api/v1/projects/proj-1")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Project deleted"

    def test_archive_project_success(self, client, mock_project_service):
        mock_project_service.archive_project.return_value = _mock_workspace(
            id="proj-1",
            workspace_id="ws-1",
            name="Archived",
            description=None,
            status="archived",
            research_goal=None,
            key_questions=None,
            session_count=0,
            paper_count=0,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )
        resp = client.post("/api/v1/projects/proj-1/archive")
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"

    def test_archive_project_not_found(self, client, mock_project_service):
        mock_project_service.archive_project.side_effect = NotFoundError("ResearchProject", "proj-none")
        resp = client.post("/api/v1/projects/proj-none/archive")
        assert resp.status_code == 404

    def test_duplicate_project_success(self, client, mock_project_service):
        mock_project_service.duplicate_project.return_value = _mock_workspace(
            id="proj-2",
            workspace_id="ws-1",
            name="Test (Copy)",
            description=None,
            status="active",
            research_goal=None,
            key_questions=None,
            session_count=0,
            paper_count=0,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )
        resp = client.post("/api/v1/projects/proj-1/duplicate")
        assert resp.status_code == 201
        assert resp.json()["id"] == "proj-2"


class TestResearchDashboardRoutes:
    def test_overview_success(self, client, mock_research_service):
        resp = client.get("/api/v1/research/overview")
        assert resp.status_code == 200
        assert resp.json()["projects"] == 2

    def test_activity_success(self, client, mock_research_service):
        resp = client.get("/api/v1/research/activity")
        assert resp.status_code == 200
        assert resp.json() == {"recentlyOpened": []}

    def test_cards_success(self, client, mock_research_service):
        resp = client.get("/api/v1/research/cards")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_recent_activity_success(self, client, mock_research_service):
        resp = client.get("/api/v1/research/recent-activity")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_notes_success(self, client, mock_research_service):
        resp = client.get("/api/v1/research/notes")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_reading_queue_success(self, client, mock_research_service):
        resp = client.get("/api/v1/research/reading-queue")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_saved_papers_success(self, client, mock_research_service):
        resp = client.get("/api/v1/research/saved-papers")
        assert resp.status_code == 200
        assert resp.json() == []


class TestResearchRoutes:
    def test_submit_query_success(self, client, mock_research_service):
        mock_research_service.submit_query.return_value = {
            "session_id": "sess-1",
            "workflow_id": "wf-1",
            "status": "submitted",
            "message": "Query submitted",
        }
        resp = client.post(
            "/api/v1/research/queries",
            json={"query": "test query", "project_id": "proj-1", "max_papers": 50},
        )
        assert resp.status_code == 201
        assert resp.json()["session_id"] == "sess-1"

    def test_submit_query_defaults(self, client, mock_research_service):
        mock_research_service.submit_query.return_value = {
            "session_id": "sess-2",
            "workflow_id": "wf-2",
            "status": "submitted",
            "message": "Query submitted",
        }
        resp = client.post(
            "/api/v1/research/queries",
            json={"query": "test", "project_id": "proj-1"},
        )
        assert resp.status_code == 201

    def test_list_sessions_success(self, client, mock_research_service):
        mock_research_service.list_sessions.return_value = ([], 0)
        resp = client.get("/api/v1/research/sessions")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_list_sessions_filter_by_project(self, client, mock_research_service):
        mock_research_service.list_sessions.return_value = ([], 0)
        resp = client.get("/api/v1/research/sessions?project_id=proj-1")
        assert resp.status_code == 200

    def test_get_session_success(self, client, mock_research_service):
        mock_research_service.get_session.return_value = _mock_project(
            id="sess-1",
            project_id="proj-1",
            status="in_progress",
            workflow_id=None,
            query="test",
            agent_phases_completed=0,
            total_tokens=0,
            total_cost=0.0,
            started_at=None,
            completed_at=None,
            error_message=None,
            created_at=datetime(2025, 1, 1),
        )
        resp = client.get("/api/v1/research/sessions/sess-1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "sess-1"

    def test_get_session_not_found(self, client, mock_research_service):
        mock_research_service.get_session.return_value = None
        resp = client.get("/api/v1/research/sessions/sess-none")
        assert resp.status_code == 404

    def test_trigger_retrieval_success(self, client, mock_research_service):
        mock_research_service.trigger_retrieval.return_value = _mock_project(
            id="sess-1",
            project_id="proj-1",
            status="retrieving",
            workflow_id=None,
            query="test",
            agent_phases_completed=1,
            total_tokens=100,
            total_cost=0.01,
            started_at=datetime(2025, 1, 1),
            completed_at=None,
            error_message=None,
            created_at=datetime(2025, 1, 1),
        )
        resp = client.post("/api/v1/research/sessions/sess-1/retrieval")
        assert resp.status_code == 200
        assert resp.json()["status"] == "retrieving"

    def test_trigger_analysis_success(self, client, mock_research_service):
        mock_research_service.trigger_analysis.return_value = _mock_project(
            id="sess-1",
            project_id="proj-1",
            status="analyzing",
            workflow_id=None,
            query="test",
            agent_phases_completed=2,
            total_tokens=200,
            total_cost=0.02,
            started_at=datetime(2025, 1, 1),
            completed_at=None,
            error_message=None,
            created_at=datetime(2025, 1, 1),
        )
        resp = client.post("/api/v1/research/sessions/sess-1/analysis")
        assert resp.status_code == 200
        assert resp.json()["status"] == "analyzing"

    def test_trigger_writing_success(self, client, mock_research_service):
        mock_research_service.trigger_writing.return_value = _mock_project(
            id="sess-1",
            project_id="proj-1",
            status="writing",
            workflow_id=None,
            query="test",
            agent_phases_completed=3,
            total_tokens=300,
            total_cost=0.03,
            started_at=datetime(2025, 1, 1),
            completed_at=None,
            error_message=None,
            created_at=datetime(2025, 1, 1),
        )
        resp = client.post("/api/v1/research/sessions/sess-1/writing")
        assert resp.status_code == 200
        assert resp.json()["status"] == "writing"

    def test_upload_pdf_success(self, client, mock_research_service):
        mock_research_service.upload_pdf.return_value = {"id": "paper-1", "status": "uploaded"}
        resp = client.post(
            "/api/v1/research/upload?workspace_id=ws-1",
            files={"file": ("test.pdf", BytesIO(b"%PDF-1.4 test"), "application/pdf")},
        )
        assert resp.status_code == 201
        assert resp.json()["id"] == "paper-1"

    def test_upload_pdf_with_project(self, client, mock_research_service):
        mock_research_service.upload_pdf.return_value = {"id": "paper-2", "status": "uploaded"}
        resp = client.post(
            "/api/v1/research/upload?workspace_id=ws-1&project_id=proj-1",
            files={"file": ("test.pdf", BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
        assert resp.status_code == 201


class TestCitationsRoutes:
    def test_list_citations_success(self, client, mock_citation_service):
        mock_citation_service.list_citations.return_value = ([], 0)
        resp = client.get("/api/v1/citations?workspace_id=ws-1")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_list_citations_missing_workspace_id(self, client, mock_citation_service):
        resp = client.get("/api/v1/citations")
        assert resp.status_code == 422

    def test_list_citations_filter_by_workspace(self, client, mock_citation_service):
        mock_citation_service.list_citations.return_value = ([], 0)
        resp = client.get("/api/v1/citations?workspace_id=ws-1")
        assert resp.status_code == 200

    def test_create_citation_success(self, client, mock_citation_service):
        mock_citation_service.create_citation.return_value = _mock_workspace(
            id="cit-1",
            workspace_id="ws-1",
            paper_id=None,
            raw_citation_text=None,
            formatted_citation=None,
            style="apa",
            source_type="journal",
            authors=["Author A"],
            title="Test Citation",
            year=2025,
            journal=None,
            volume=None,
            issue=None,
            pages=None,
            doi=None,
            url=None,
            isbn=None,
            publisher=None,
            accessed_date=None,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )
        resp = client.post(
            "/api/v1/citations?workspace_id=ws-1",
            json={"title": "Test Citation", "source_type": "journal"},
        )
        assert resp.status_code == 201
        assert resp.json()["title"] == "Test Citation"

    def test_create_citation_validation_error(self, client):
        resp = client.post("/api/v1/citations", json={})
        assert resp.status_code == 422

    def test_get_citation_success(self, client, mock_citation_service):
        mock_citation_service.get_citation.return_value = _mock_workspace(
            id="cit-1",
            workspace_id="ws-1",
            paper_id=None,
            raw_citation_text=None,
            formatted_citation=None,
            style="apa",
            source_type="journal",
            authors=[],
            title="Test",
            year=2025,
            journal=None,
            volume=None,
            issue=None,
            pages=None,
            doi=None,
            url=None,
            isbn=None,
            publisher=None,
            accessed_date=None,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )
        resp = client.get("/api/v1/citations/cit-1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "cit-1"

    def test_get_citation_not_found(self, client, mock_citation_service):
        mock_citation_service.get_citation.side_effect = NotFoundError("Citation", "cit-none")
        resp = client.get("/api/v1/citations/cit-none")
        assert resp.status_code == 404

    def test_update_citation_success(self, client, mock_citation_service):
        mock_citation_service.update_citation.return_value = _mock_workspace(
            id="cit-1",
            workspace_id="ws-1",
            paper_id=None,
            raw_citation_text=None,
            formatted_citation=None,
            style="mla",
            source_type="journal",
            authors=[],
            title="Updated",
            year=2025,
            journal=None,
            volume=None,
            issue=None,
            pages=None,
            doi=None,
            url=None,
            isbn=None,
            publisher=None,
            accessed_date=None,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )
        resp = client.patch("/api/v1/citations/cit-1", json={"title": "Updated", "style": "mla"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"

    def test_update_citation_not_found(self, client, mock_citation_service):
        mock_citation_service.update_citation.side_effect = NotFoundError("Citation", "cit-none")
        resp = client.patch("/api/v1/citations/cit-none", json={"title": "Nope"})
        assert resp.status_code == 404

    def test_delete_citation_success(self, client, mock_citation_service):
        resp = client.delete("/api/v1/citations/cit-1")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Citation deleted"

    def test_export_citations_success(self, client, mock_citation_service):
        mock_citation_service.export_citations.return_value = {
            "format": "bibtex",
            "content": "@article{...}",
            "filename": "citations.bib",
        }
        resp = client.post(
            "/api/v1/citations/export",
            json={"citation_ids": ["cit-1", "cit-2"], "format": "bibtex"},
        )
        assert resp.status_code == 200
        assert resp.json()["format"] == "bibtex"

    def test_get_citation_summary_missing_workspace_id(self, client, mock_citation_service):
        resp = client.get("/api/v1/citations/summary")
        assert resp.status_code == 422

    def test_get_citation_summary_with_workspace(self, client, mock_citation_service):
        mock_citation_service.get_library_summary.return_value = {
            "total_citations": 3,
            "by_style": {"apa": 3},
            "by_source_type": {"journal": 3},
        }
        resp = client.get("/api/v1/citations/summary?workspace_id=ws-1")
        assert resp.status_code == 200
        assert resp.json()["total_citations"] == 3


class TestLibraryRoutes:
    def test_list_papers_success(self, client, mock_paper_service):
        mock_paper_service.list_papers.return_value = ([], 0)
        resp = client.get("/api/v1/library?workspace_id=ws-1")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_list_papers_missing_workspace_id(self, client, mock_paper_service):
        resp = client.get("/api/v1/library")
        assert resp.status_code == 422

    def test_list_papers_with_filters(self, client, mock_paper_service):
        mock_paper_service.list_papers.return_value = ([], 0)
        resp = client.get("/api/v1/library?workspace_id=ws-1&project_id=proj-1&status=processed")
        assert resp.status_code == 200

    def test_upload_paper_success(self, client, mock_paper_service):
        mock_paper_service.upload_paper.return_value = _mock_workspace(
            id="paper-1",
            title="test.pdf",
            file_type="pdf",
            file_size=1234,
            status="uploaded",
            version=1,
            created_at=datetime(2025, 1, 1),
        )
        resp = client.post(
            "/api/v1/library/upload?workspace_id=ws-1",
            files={"file": ("test.pdf", BytesIO(b"%PDF-1.4 data"), "application/pdf")},
        )
        assert resp.status_code == 201
        assert resp.json()["id"] == "paper-1"

    def test_upload_paper_with_project(self, client, mock_paper_service):
        mock_paper_service.upload_paper.return_value = _mock_workspace(
            id="paper-2",
            title="paper.pdf",
            file_type="pdf",
            file_size=5678,
            status="uploaded",
            version=1,
            created_at=datetime(2025, 1, 1),
        )
        resp = client.post(
            "/api/v1/library/upload?workspace_id=ws-1&project_id=proj-1",
            files={"file": ("paper.pdf", BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
        assert resp.status_code == 201

    def test_get_paper_success(self, client, mock_paper_service):
        mock_paper_service.get_paper.return_value = _mock_workspace(
            id="paper-1",
            workspace_id="ws-1",
            project_id=None,
            title="Test Paper",
            authors=["Author A"],
            abstract=None,
            source=None,
            file_path=None,
            file_type="pdf",
            file_size=1234,
            doi=None,
            arxiv_id=None,
            url=None,
            publication_year=None,
            venue=None,
            citation_count=0,
            status="processed",
            version=1,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )
        resp = client.get("/api/v1/library/paper-1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "paper-1"

    def test_get_paper_not_found(self, client, mock_paper_service):
        mock_paper_service.get_paper.return_value = None
        resp = client.get("/api/v1/library/paper-none")
        assert resp.status_code == 404

    def test_update_paper_success(self, client, mock_paper_service):
        mock_paper_service.update_paper.return_value = _mock_workspace(
            id="paper-1",
            workspace_id="ws-1",
            project_id=None,
            title="Updated Title",
            authors=["Author A"],
            abstract=None,
            source=None,
            file_path=None,
            file_type="pdf",
            file_size=1234,
            doi="10.1234/test",
            arxiv_id=None,
            url=None,
            publication_year=2025,
            venue=None,
            citation_count=0,
            status="processed",
            version=1,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )
        resp = client.patch("/api/v1/library/paper-1", json={"title": "Updated Title", "doi": "10.1234/test"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    def test_update_paper_not_found(self, client, mock_paper_service):
        mock_paper_service.update_paper.return_value = None
        resp = client.patch("/api/v1/library/paper-none", json={"title": "Nope"})
        assert resp.status_code == 404

    def test_delete_paper_success(self, client, mock_paper_service):
        resp = client.delete("/api/v1/library/paper-1")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Paper deleted"

    def test_replace_paper_success(self, client, mock_paper_service):
        mock_paper_service.replace_paper.return_value = _mock_workspace(
            id="paper-1",
            title="replaced.pdf",
            file_type="pdf",
            file_size=999,
            status="uploaded",
            version=2,
            created_at=datetime(2025, 1, 1),
        )
        resp = client.post(
            "/api/v1/library/paper-1/replace",
            files={"file": ("replaced.pdf", BytesIO(b"%PDF-2.0 data"), "application/pdf")},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == "paper-1"

    def test_get_paper_versions_success(self, client, mock_paper_service):
        mock_paper_service.get_paper_versions.return_value = [
            MagicMock(
                version=1,
                file_type="pdf",
                file_size=1000,
                created_at=datetime(2025, 1, 1),
            ),
            MagicMock(
                version=2,
                file_type="pdf",
                file_size=2000,
                created_at=datetime(2025, 1, 2),
            ),
        ]
        resp = client.get("/api/v1/library/paper-1/versions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) == 2

    def test_check_duplicate_by_hash(self, client, mock_paper_service):
        mock_paper_service.check_duplicate.return_value = {
            "is_duplicate": True,
            "existing_paper": None,
            "confidence": 0.95,
        }
        resp = client.post("/api/v1/library/check-duplicate?workspace_id=ws-1&content_hash=abc123")
        assert resp.status_code == 200
        assert resp.json()["is_duplicate"] is True

    def test_check_duplicate_by_doi(self, client, mock_paper_service):
        mock_paper_service.check_duplicate.return_value = {
            "is_duplicate": False,
            "existing_paper": None,
            "confidence": 0.0,
        }
        resp = client.post("/api/v1/library/check-duplicate?workspace_id=ws-1&doi=10.1234/test")
        assert resp.status_code == 200
        assert resp.json()["is_duplicate"] is False

    def test_check_duplicate_no_params(self, client, mock_paper_service):
        mock_paper_service.check_duplicate.return_value = {
            "is_duplicate": False,
            "existing_paper": None,
            "confidence": 0.0,
        }
        resp = client.post("/api/v1/library/check-duplicate?workspace_id=ws-1")
        assert resp.status_code == 200


class TestDocumentsRoutes:
    def test_generate_document_success(self, client, mock_document_service):
        mock_document_service.generate_document.return_value = {
            "id": "doc-1",
            "status": "generated",
        }
        resp = client.post(
            "/api/v1/documents/generate",
            json={
                "workspace_id": "ws-1",
                "format": "markdown",
                "title": "Test Doc",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["id"] == "doc-1"

    def test_generate_document_with_optional_fields(self, client, mock_document_service):
        mock_document_service.generate_document.return_value = {
            "id": "doc-2",
            "status": "generated",
        }
        resp = client.post(
            "/api/v1/documents/generate",
            json={
                "workspace_id": "ws-1",
                "session_id": "sess-1",
                "project_id": "proj-1",
                "format": "pdf",
                "title": "Report",
                "template": "default",
                "sections": ["intro", "conclusion"],
            },
        )
        assert resp.status_code == 201

    def test_list_documents_success(self, client, mock_document_service):
        mock_document_service.list_documents.return_value = ([], 0)
        resp = client.get("/api/v1/documents")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_list_documents_filter_by_workspace(self, client, mock_document_service):
        mock_document_service.list_documents.return_value = ([], 0)
        resp = client.get("/api/v1/documents?workspace_id=ws-1")
        assert resp.status_code == 200

    def test_get_document_success(self, client, mock_document_service):
        mock_document_service.get_document.return_value = _mock_workspace(
            id="doc-1",
            workspace_id="ws-1",
            session_id=None,
            format="markdown",
            title="Test Doc",
            content="# Hello",
            file_path=None,
            file_size=100,
            status="completed",
            version=1,
            citation_count=0,
            template_used=None,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )
        resp = client.get("/api/v1/documents/doc-1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "doc-1"

    def test_get_document_not_found(self, client, mock_document_service):
        mock_document_service.get_document.return_value = None
        resp = client.get("/api/v1/documents/doc-none")
        assert resp.status_code == 404

    def test_export_document_success(self, client, mock_document_service):
        mock_document_service.export_document.return_value = {
            "content": "# Exported",
            "format": "markdown",
            "filename": "doc-1.md",
        }
        resp = client.post(
            "/api/v1/documents/doc-1/export",
            json={"format": "markdown"},
        )
        assert resp.status_code == 200
        assert resp.json()["format"] == "markdown"


class TestDashboardRoutes:
    def test_get_full_dashboard_success(self, client, mock_dashboard_service):
        mock_dashboard_service.get_full_dashboard.return_value = {
            "workflow": {"workflow_id": "wf-1", "status": "completed", "progress_pct": 100.0, "elapsed_seconds": 10.5},
            "tokens": {"total_tokens": 5000, "prompt_tokens": 3000, "completion_tokens": 2000, "estimated_cost": 0.05},
            "providers": [],
            "evaluation_scores": [],
            "timeline": [],
        }
        resp = client.get("/api/v1/dashboard/workflows/wf-1")
        assert resp.status_code == 200
        assert resp.json()["workflow"]["workflow_id"] == "wf-1"

    def test_get_full_dashboard_not_found(self, client, mock_dashboard_service):
        mock_dashboard_service.get_full_dashboard.side_effect = NotFoundError("Workflow", "wf-none")
        resp = client.get("/api/v1/dashboard/workflows/wf-none")
        assert resp.status_code == 404

    def test_get_workflow_status_success(self, client, mock_dashboard_service):
        mock_dashboard_service.get_workflow_status.return_value = {
            "workflow_id": "wf-1",
            "status": "running",
            "current_phase": "retrieval",
            "current_agent": "searcher",
            "progress_pct": 50.0,
            "started_at": "2025-01-01T00:00:00",
            "completed_at": None,
            "elapsed_seconds": 100.0,
        }
        resp = client.get("/api/v1/dashboard/workflows/wf-1/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_get_workflow_status_not_found(self, client, mock_dashboard_service):
        mock_dashboard_service.get_workflow_status.side_effect = NotFoundError("Workflow", "wf-none")
        resp = client.get("/api/v1/dashboard/workflows/wf-none/status")
        assert resp.status_code == 404

    def test_get_token_usage_success(self, client, mock_dashboard_service):
        mock_dashboard_service.get_token_usage.return_value = {
            "total_tokens": 5000,
            "prompt_tokens": 3000,
            "completion_tokens": 2000,
            "estimated_cost": 0.05,
        }
        resp = client.get("/api/v1/dashboard/workflows/wf-1/tokens")
        assert resp.status_code == 200
        assert resp.json()["total_tokens"] == 5000

    def test_get_token_usage_not_found(self, client, mock_dashboard_service):
        mock_dashboard_service.get_token_usage.side_effect = NotFoundError("Workflow", "wf-none")
        resp = client.get("/api/v1/dashboard/workflows/wf-none/tokens")
        assert resp.status_code == 404

    def test_get_provider_usage_success(self, client, mock_dashboard_service):
        mock_dashboard_service.get_provider_usage.return_value = [
            {"provider": "openai", "model": "gpt-4", "calls": 10, "tokens": 5000, "cost": 0.05}
        ]
        resp = client.get("/api/v1/dashboard/workflows/wf-1/providers")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_evaluation_scores_success(self, client, mock_dashboard_service):
        mock_dashboard_service.get_evaluation_scores.return_value = [
            {"metric": "relevance", "score": 0.85, "details": None}
        ]
        resp = client.get("/api/v1/dashboard/workflows/wf-1/evaluation")
        assert resp.status_code == 200
        assert resp.json()[0]["metric"] == "relevance"

    def test_get_event_timeline_success(self, client, mock_dashboard_service):
        mock_dashboard_service.get_event_timeline.return_value = [
            {"event": "phase_completed", "phase": "retrieval", "timestamp": "2025-01-01T00:01:00"}
        ]
        resp = client.get("/api/v1/dashboard/workflows/wf-1/timeline")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestSearchRoutes:
    def test_unified_search_success(self, client, mock_search_service):
        mock_search_service.search.return_value = (
            [
                {"id": "res-1", "type": "paper", "title": "Result 1", "snippet": "...", "score": 0.95, "metadata": {}}
            ],
            1,
        )
        resp = client.post(
            "/api/v1/search",
            json={
                "query": "test query",
                "scope": "papers",
                "page": 1,
                "page_size": 20,
            },
        )
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1
        assert resp.json()["total"] == 1

    def test_unified_search_empty_results(self, client, mock_search_service):
        mock_search_service.search.return_value = ([], 0)
        resp = client.post(
            "/api/v1/search",
            json={
                "query": "nonexistent",
                "scope": "workspace",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["results"] == []
        assert resp.json()["total"] == 0

    def test_unified_search_with_all_filters(self, client, mock_search_service):
        mock_search_service.search.return_value = ([], 0)
        resp = client.post(
            "/api/v1/search",
            json={
                "query": "test",
                "scope": "semantic",
                "workspace_id": "ws-1",
                "project_id": "proj-1",
                "page": 2,
                "page_size": 10,
                "filters": {"year": 2025},
            },
        )
        assert resp.status_code == 200

    def test_unified_search_validation_error(self, client):
        resp = client.post("/api/v1/search", json={})
        assert resp.status_code == 422

    def test_unified_search_all_scopes(self, client, mock_search_service):
        for scope in ["workspace", "papers", "citations", "projects", "semantic"]:
            mock_search_service.search.return_value = ([], 0)
            resp = client.post("/api/v1/search", json={"query": "test", "scope": scope})
            assert resp.status_code == 200


class TestEdgeCases:
    def test_workspace_invalid_page_param(self, client):
        resp = client.get("/api/v1/workspaces?page=0")
        assert resp.status_code == 422

    def test_workspace_invalid_page_size(self, client):
        resp = client.get("/api/v1/workspaces?page_size=200")
        assert resp.status_code == 422

    def test_project_invalid_page_param(self, client):
        resp = client.get("/api/v1/projects?page=-1")
        assert resp.status_code == 422

    def test_research_submit_query_validation_error(self, client):
        resp = client.post("/api/v1/research/queries", json={"query": "test"})
        assert resp.status_code == 422

    def test_citation_export_invalid_format(self, client):
        resp = client.post(
            "/api/v1/citations/export",
            json={"citation_ids": ["cit-1"], "format": "invalid"},
        )
        assert resp.status_code == 422

    def test_document_generate_validation_error(self, client):
        resp = client.post("/api/v1/documents/generate", json={"workspace_id": "ws-1"})
        assert resp.status_code == 422

    def test_dashboard_providers_empty(self, client, mock_dashboard_service):
        mock_dashboard_service.get_provider_usage.return_value = []
        resp = client.get("/api/v1/dashboard/workflows/wf-1/providers")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_dashboard_evaluation_empty(self, client, mock_dashboard_service):
        mock_dashboard_service.get_evaluation_scores.return_value = []
        resp = client.get("/api/v1/dashboard/workflows/wf-1/evaluation")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_citation_export_ris_format(self, client, mock_citation_service):
        mock_citation_service.export_citations.return_value = {
            "format": "ris",
            "content": "TY  - JOUR\nTI  - Test",
            "filename": "citations.ris",
        }
        resp = client.post(
            "/api/v1/citations/export",
            json={"citation_ids": ["cit-1"], "format": "ris"},
        )
        assert resp.status_code == 200
        assert resp.json()["format"] == "ris"

    def test_workspace_create_with_all_fields(self, client, mock_workspace_service):
        mock_workspace_service.create_workspace.return_value = _mock_workspace(
            id="ws-2",
            name="Full Workspace",
            description="A description",
            research_topic="AI",
            status="active",
            owner_id="user-1",
            member_count=1,
            paper_count=0,
            workflow_count=0,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )
        resp = client.post(
            "/api/v1/workspaces",
            json={"name": "Full Workspace", "description": "A description", "research_topic": "AI"},
        )
        assert resp.status_code == 201
        assert resp.json()["research_topic"] == "AI"

    def test_document_export_pdf_format(self, client, mock_document_service):
        mock_document_service.export_document.return_value = {
            "content": "%PDF-1.4...",
            "format": "pdf",
            "filename": "doc-1.pdf",
        }
        resp = client.post(
            "/api/v1/documents/doc-1/export",
            json={"format": "pdf"},
        )
        assert resp.status_code == 200


class TestQualityCheckRoutes:
    @pytest.mark.parametrize(
        "capability",
        ["plagiarism", "ai_detection", "publication_readiness", "submission_assistant"],
    )
    def test_check_reports_not_configured(self, client, capability):
        resp = client.post(
            f"/api/v1/quality/{capability}/check",
            json={"text": "Some draft text to check."},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "not_configured"
        assert body["capability"] == capability

    def test_check_rejects_unknown_capability(self, client):
        resp = client.post(
            "/api/v1/quality/not-a-real-capability/check",
            json={"text": "Some draft text to check."},
        )
        assert resp.status_code == 422
