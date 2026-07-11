"""
Tests for Milestone 5 schemas and models.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.models.citation import Citation
from app.models.document import Document
from app.models.research_paper import ResearchPaper
from app.models.research_project import ResearchProject
from app.models.research_session import ResearchSession
from app.models.workspace import Workspace
from app.schemas.citation import (
    CitationCreate,
    CitationExportRequest,
    CitationExportResponse,
    CitationLibrarySummary,
    CitationResponse,
    CitationUpdate,
)
from app.schemas.common import ErrorResponse, MessageResponse, PaginatedResponse
from app.schemas.dashboard import (
    DashboardResponse,
    EvaluationScoreResponse,
    ProviderUsageResponse,
    TokenUsageResponse,
    WorkflowStatusResponse,
)
from app.schemas.document import DocumentExportRequest, DocumentGenerateRequest, DocumentResponse
from app.schemas.library import (
    DuplicateCheckResponse,
    PaperResponse,
    PaperUpdate,
    PaperUploadResponse,
    PaperVersionResponse,
)
from app.schemas.research import (
    ResearchProjectCreate,
    ResearchProjectResponse,
    ResearchProjectUpdate,
    ResearchSessionCreate,
    ResearchSessionResponse,
    ResearchSubmission,
    ResearchSubmissionResponse,
)
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate

# =============================================================================
# Schema Tests
# =============================================================================

class TestWorkspaceCreate:
    def test_valid_minimal(self):
        s = WorkspaceCreate(name="my workspace")
        assert s.name == "my workspace"
        assert s.description is None
        assert s.research_topic is None

    def test_valid_full(self):
        s = WorkspaceCreate(name="research lab", description="A lab", research_topic="AI")
        assert s.name == "research lab"
        assert s.description == "A lab"
        assert s.research_topic == "AI"

    def test_name_min_length(self):
        with pytest.raises(ValueError, match="at least 1 character"):
            WorkspaceCreate(name="")

    def test_name_max_length(self):
        with pytest.raises(ValueError, match="at most 255 characters"):
            WorkspaceCreate(name="x" * 256)

    def test_description_max_length(self):
        with pytest.raises(ValueError):
            WorkspaceCreate(name="ok", description="x" * 2001)

    def test_serialization_roundtrip(self):
        s = WorkspaceCreate(name="test", description="desc")
        d = s.model_dump()
        assert d["name"] == "test"
        assert d["description"] == "desc"
        s2 = WorkspaceCreate(**d)
        assert s2.name == s.name


class TestWorkspaceUpdate:
    def test_all_none(self):
        s = WorkspaceUpdate()
        assert s.name is None
        assert s.description is None
        assert s.research_topic is None
        assert s.status is None

    def test_with_values(self):
        s = WorkspaceUpdate(name="new name", status="archived")
        assert s.name == "new name"
        assert s.status == "archived"

    def test_invalid_status(self):
        with pytest.raises(ValueError):
            WorkspaceUpdate(status="invalid")

    def test_serialization_roundtrip(self):
        s = WorkspaceUpdate(name="x", description="y")
        s2 = WorkspaceUpdate(**s.model_dump())
        assert s2.name == "x"


class TestWorkspaceResponse:
    def test_minimal(self):
        s = WorkspaceResponse(id="1", name="w", owner_id="u1")
        assert s.status == "active"
        assert s.member_count == 0
        assert s.paper_count == 0
        assert s.workflow_count == 0

    def test_from_attributes_config(self):
        assert WorkspaceResponse.model_config.get("from_attributes") is True

    def test_full(self):
        dt = datetime.now(UTC)
        s = WorkspaceResponse(
            id="1", name="w", description="d", research_topic="t",
            status="archived", owner_id="u1", member_count=5, paper_count=3,
            workflow_count=2, created_at=dt, updated_at=dt,
        )
        assert s.description == "d"
        assert s.status == "archived"
        assert s.member_count == 5

    def test_serialization_roundtrip(self):
        s = WorkspaceResponse(id="a", name="n", owner_id="o")
        d = s.model_dump()
        assert d["id"] == "a"
        s2 = WorkspaceResponse(**d)
        assert s2.id == s.id


class TestResearchProjectCreate:
    def test_valid(self):
        s = ResearchProjectCreate(workspace_id="w1", name="Project A")
        assert s.name == "Project A"
        assert s.description is None
        assert s.research_goal is None
        assert s.key_questions is None

    def test_with_all_fields(self):
        s = ResearchProjectCreate(
            workspace_id="w1", name="P", description="desc",
            research_goal="goal", key_questions=["q1", "q2"],
        )
        assert s.key_questions == ["q1", "q2"]

    def test_name_min_length(self):
        with pytest.raises(ValueError):
            ResearchProjectCreate(workspace_id="w1", name="")

    def test_name_max_length(self):
        with pytest.raises(ValueError):
            ResearchProjectCreate(workspace_id="w1", name="x" * 256)


class TestResearchProjectUpdate:
    def test_all_none(self):
        s = ResearchProjectUpdate()
        assert s.name is None

    def test_with_values(self):
        s = ResearchProjectUpdate(name="new", key_questions=["q"], status="archived")
        assert s.status == "archived"

    def test_invalid_status(self):
        with pytest.raises(ValueError):
            ResearchProjectUpdate(status="unknown")


class TestResearchProjectResponse:
    def test_defaults(self):
        s = ResearchProjectResponse(id="1", workspace_id="w1", name="n")
        assert s.status == "active"
        assert s.session_count == 0
        assert s.paper_count == 0

    def test_from_attributes_config(self):
        assert ResearchProjectResponse.model_config.get("from_attributes") is True

    def test_serialization(self):
        s = ResearchProjectResponse(id="1", workspace_id="w1", name="n")
        d = s.model_dump()
        assert d["session_count"] == 0


class TestResearchSessionCreate:
    def test_valid(self):
        s = ResearchSessionCreate(project_id="p1", query="search papers")
        assert s.project_id == "p1"
        assert s.query == "search papers"

    def test_serialization(self):
        s = ResearchSessionCreate(project_id="p1", query="q")
        assert ResearchSessionCreate(**s.model_dump()).project_id == "p1"


class TestResearchSessionResponse:
    def test_defaults(self):
        s = ResearchSessionResponse(id="s1", project_id="p1", status="running", query="q")
        assert s.agent_phases_completed == 0
        assert s.total_tokens == 0
        assert s.total_cost == 0.0

    def test_from_attributes_config(self):
        assert ResearchSessionResponse.model_config.get("from_attributes") is True

    def test_full(self):
        s = ResearchSessionResponse(
            id="s1", project_id="p1", status="completed", workflow_id="wf1",
            query="q", agent_phases_completed=3, total_tokens=500,
            total_cost=0.02, started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        assert s.total_cost == 0.02


class TestResearchSubmission:
    def test_defaults(self):
        s = ResearchSubmission(query="test query", project_id="p1")
        assert s.max_papers == 50
        assert s.research_direction is None

    def test_custom_max_papers(self):
        s = ResearchSubmission(query="q", project_id="p1", max_papers=10)
        assert s.max_papers == 10


class TestResearchSubmissionResponse:
    def test_required_fields(self):
        s = ResearchSubmissionResponse(session_id="s1", workflow_id="w1", status="ok", message="done")
        assert s.session_id == "s1"
        assert s.workflow_id == "w1"


class TestCitationCreate:
    def test_defaults(self):
        s = CitationCreate(title="My Paper")
        assert s.style == "apa"
        assert s.source_type == "journal"
        assert s.paper_id is None

    def test_custom_style(self):
        s = CitationCreate(title="T", style="mla", source_type="book")
        assert s.style == "mla"
        assert s.source_type == "book"

    def test_all_optional_none(self):
        s = CitationCreate(title="T")
        assert s.authors is None
        assert s.year is None


class TestCitationUpdate:
    def test_all_none(self):
        s = CitationUpdate()
        assert s.title is None
        assert s.style is None

    def test_partial(self):
        s = CitationUpdate(title="New Title", year=2024)
        assert s.title == "New Title"
        assert s.year == 2024


class TestCitationResponse:
    def test_defaults(self):
        s = CitationResponse(id="c1", workspace_id="w1", title="T")
        assert s.style == "apa"
        assert s.source_type == "journal"

    def test_from_attributes_config(self):
        assert CitationResponse.model_config.get("from_attributes") is True


class TestCitationExportRequest:
    def test_valid(self):
        s = CitationExportRequest(citation_ids=["c1", "c2"], format="bibtex")
        assert s.format == "bibtex"

    def test_invalid_format(self):
        with pytest.raises(ValueError):
            CitationExportRequest(citation_ids=["c1"], format="txt")


class TestCitationExportResponse:
    def test_fields(self):
        s = CitationExportResponse(format="ris", content="content", filename="refs.ris")
        assert s.filename == "refs.ris"


class TestCitationLibrarySummary:
    def test_fields(self):
        s = CitationLibrarySummary(total_citations=10, by_style={"apa": 5}, by_source_type={"journal": 8})
        assert s.total_citations == 10
        assert s.by_style["apa"] == 5


class TestPaperUploadResponse:
    def test_defaults(self):
        s = PaperUploadResponse(id="p1", title="Paper", file_type="pdf", status="uploaded")
        assert s.version == 1
        assert s.file_size is None

    def test_from_attributes_config(self):
        assert PaperUploadResponse.model_config.get("from_attributes") is True

    def test_serialization(self):
        s = PaperUploadResponse(id="p1", title="T", file_type="pdf", status="done")
        assert PaperUploadResponse(**s.model_dump()).id == "p1"


class TestPaperUpdate:
    def test_all_none(self):
        s = PaperUpdate()
        assert s.title is None
        assert s.authors is None

    def test_with_values(self):
        s = PaperUpdate(title="Updated", authors=["Alice"], publication_year=2023)
        assert s.publication_year == 2023


class TestPaperResponse:
    def test_defaults(self):
        s = PaperResponse(id="p1", workspace_id="w1", title="Paper")
        assert s.citation_count == 0
        assert s.version == 1

    def test_from_attributes_config(self):
        assert PaperResponse.model_config.get("from_attributes") is True

    def test_full(self):
        s = PaperResponse(id="p1", workspace_id="w1", title="T", authors=["A", "B"],
                          citation_count=5, version=3)
        assert s.authors == ["A", "B"]
        assert s.citation_count == 5


class TestPaperVersionResponse:
    def test_fields(self):
        s = PaperVersionResponse(version=2, file_type="pdf", file_size=1024)
        assert s.version == 2


class TestDuplicateCheckResponse:
    def test_duplicate_true(self):
        paper = PaperResponse(id="p1", workspace_id="w1", title="Existing")
        s = DuplicateCheckResponse(is_duplicate=True, existing_paper=paper, confidence=0.95)
        assert s.is_duplicate is True
        assert s.confidence == 0.95

    def test_duplicate_false(self):
        s = DuplicateCheckResponse(is_duplicate=False, existing_paper=None, confidence=0.0)
        assert s.is_duplicate is False


class TestDocumentGenerateRequest:
    def test_valid(self):
        s = DocumentGenerateRequest(workspace_id="w1", format="markdown", title="Doc")
        assert s.format == "markdown"
        assert s.session_id is None

    def test_invalid_format(self):
        with pytest.raises(ValueError):
            DocumentGenerateRequest(workspace_id="w1", format="txt", title="Doc")

    def test_with_all_optionals(self):
        s = DocumentGenerateRequest(
            workspace_id="w1", session_id="s1", project_id="p1",
            format="pdf", title="Doc", template="default", sections=["Intro"],
        )
        assert s.sections == ["Intro"]


class TestDocumentResponse:
    def test_defaults(self):
        s = DocumentResponse(id="d1", workspace_id="w1", format="md", title="T", status="draft")
        assert s.version == 1
        assert s.citation_count == 0

    def test_from_attributes_config(self):
        assert DocumentResponse.model_config.get("from_attributes") is True


class TestDocumentExportRequest:
    def test_valid(self):
        s = DocumentExportRequest(format="html")
        assert s.format == "html"

    def test_invalid(self):
        with pytest.raises(ValueError):
            DocumentExportRequest(format="xml")


class TestDashboardSchemas:
    def test_workflow_status(self):
        s = WorkflowStatusResponse(
            workflow_id="wf1", status="running", progress_pct=50.0, elapsed_seconds=120.0,
        )
        assert s.progress_pct == 50.0

    def test_token_usage(self):
        s = TokenUsageResponse(total_tokens=1000, prompt_tokens=600, completion_tokens=400, estimated_cost=0.02)
        assert s.total_tokens == 1000

    def test_provider_usage(self):
        s = ProviderUsageResponse(provider="openai", model="gpt-4", calls=10, tokens=5000, cost=0.1)
        assert s.calls == 10

    def test_evaluation_score(self):
        s = EvaluationScoreResponse(metric="accuracy", score=0.95)
        assert s.details is None

    def test_evaluation_score_with_details(self):
        s = EvaluationScoreResponse(metric="f1", score=0.89, details={"tp": 10})
        assert s.details == {"tp": 10}

    def test_dashboard_response(self):
        s = DashboardResponse(
            workflow=WorkflowStatusResponse(workflow_id="w", status="ok", progress_pct=100.0, elapsed_seconds=0.0),
            tokens=TokenUsageResponse(total_tokens=0, prompt_tokens=0, completion_tokens=0, estimated_cost=0.0),
            providers=[ProviderUsageResponse(provider="p", model="m", calls=0, tokens=0, cost=0.0)],
            evaluation_scores=[EvaluationScoreResponse(metric="m", score=1.0)],
            timeline=[{"phase": "done"}],
        )
        assert s.workflow.status == "ok"
        assert s.timeline == [{"phase": "done"}]


class TestSearchRequest:
    def test_defaults(self):
        s = SearchRequest(query="test", scope="papers")
        assert s.page == 1
        assert s.page_size == 20
        assert s.filters is None

    def test_ge_page(self):
        with pytest.raises(ValueError):
            SearchRequest(query="t", scope="papers", page=0)

    def test_ge_page_size(self):
        with pytest.raises(ValueError):
            SearchRequest(query="t", scope="papers", page_size=0)

    def test_le_page_size(self):
        with pytest.raises(ValueError):
            SearchRequest(query="t", scope="papers", page_size=101)

    def test_boundary_page_size(self):
        s = SearchRequest(query="t", scope="papers", page_size=1)
        assert s.page_size == 1
        s2 = SearchRequest(query="t", scope="papers", page_size=100)
        assert s2.page_size == 100

    def test_invalid_scope(self):
        with pytest.raises(ValueError):
            SearchRequest(query="t", scope="invalid")


class TestSearchResult:
    def test_minimal(self):
        s = SearchResult(id="1", type="paper", title="T", snippet="snip", score=0.5)
        assert s.metadata == {}

    def test_with_metadata(self):
        s = SearchResult(id="1", type="citation", title="T", snippet="snip", score=0.9, metadata={"key": "val"})
        assert s.metadata["key"] == "val"

    def test_invalid_type(self):
        with pytest.raises(ValueError):
            SearchResult(id="1", type="invalid", title="T", snippet="s", score=0.0)


class TestSearchResponse:
    def test_fields(self):
        results = [SearchResult(id="1", type="paper", title="T", snippet="s", score=1.0)]
        s = SearchResponse(results=results, total=1, page=1, page_size=20, total_pages=1)
        assert s.total == 1
        assert len(s.results) == 1


class TestCommonSchemas:
    def test_paginated_response_int(self):
        s = PaginatedResponse[int](items=[1, 2, 3], total=3, page=1, page_size=10, total_pages=1)
        assert s.items == [1, 2, 3]

    def test_paginated_response_str(self):
        s = PaginatedResponse[str](items=["a"], total=1, page=1, page_size=10, total_pages=1)
        assert s.items == ["a"]

    def test_error_response_minimal(self):
        s = ErrorResponse(detail="Not found")
        assert s.error_code is None
        assert s.errors is None

    def test_error_response_full(self):
        s = ErrorResponse(detail="Validation error", error_code="VAL001", errors={"field": "required"})
        assert s.error_code == "VAL001"

    def test_message_response(self):
        s = MessageResponse(message="ok")
        assert s.status == "ok"

    def test_message_response_custom_status(self):
        s = MessageResponse(message="created", status="created")
        assert s.status == "created"


class TestEdgeCases:
    def test_workspace_create_empty_string_rejected(self):
        with pytest.raises(ValueError):
            WorkspaceCreate(name="")

    def test_workspace_update_empty_string_accepted(self):
        s = WorkspaceUpdate(name="")
        assert s.name == ""

    def test_citation_create_empty_title_rejected(self):
        with pytest.raises(ValueError):
            CitationCreate(title="")

    def test_search_request_empty_query_rejected(self):
        with pytest.raises(ValueError):
            SearchRequest(query="", scope="papers")

    def test_research_project_create_empty_name_rejected(self):
        with pytest.raises(ValueError):
            ResearchProjectCreate(workspace_id="w1", name="")

    def test_none_serialization_roundtrip(self):
        s = WorkspaceCreate(name="test")
        d = s.model_dump()
        assert d["description"] is None
        s2 = WorkspaceCreate(**d)
        assert s2.description is None


class TestSerializationRoundTrips:
    def test_citation_create_roundtrip(self):
        s = CitationCreate(title="Paper", authors=["A"], year=2024, doi="10.1234/test")
        d = s.model_dump()
        s2 = CitationCreate(**d)
        assert s2.doi == "10.1234/test"
        assert s2.authors == ["A"]

    def test_search_request_roundtrip(self):
        s = SearchRequest(query="ml", scope="papers", page=2, page_size=50)
        d = s.model_dump()
        s2 = SearchRequest(**d)
        assert s2.page == 2
        assert s2.page_size == 50

    def test_citation_export_request_roundtrip(self):
        s = CitationExportRequest(citation_ids=["c1"], format="ieee")
        d = s.model_dump()
        s2 = CitationExportRequest(**d)
        assert s2.format == "ieee"

    def test_document_generate_request_roundtrip(self):
        s = DocumentGenerateRequest(workspace_id="w1", format="markdown", title="Doc")
        d = s.model_dump()
        s2 = DocumentGenerateRequest(**d)
        assert s2.format == "markdown"


# =============================================================================
# SQLAlchemy Model Tests
# =============================================================================

class TestWorkspaceModel:
    def test_tablename(self):
        assert Workspace.__tablename__ == "workspaces"

    def test_construct_with_required(self):
        ws = Workspace(name="Test Workspace", owner_id="user-1")
        assert ws.name == "Test Workspace"
        assert ws.owner_id == "user-1"

    def test_default_values(self):
        assert Workspace.__table__.c.status.default.arg == "active"

    def test_uuid_generation(self):
        col = Workspace.__table__.c.id
        assert col.default is not None

    def test_unique_uuids(self):
        import uuid
        ws1 = Workspace(id=str(uuid.uuid4()), name="A", owner_id="u1")
        ws2 = Workspace(id=str(uuid.uuid4()), name="B", owner_id="u2")
        assert ws1.id != ws2.id

    def test_datetime_defaults(self):
        col = Workspace.__table__.c.created_at
        assert col.default is not None

    def test_nullable_fields(self):
        ws = Workspace(name="Nullable Test", owner_id="u1")
        assert ws.description is None
        assert ws.research_topic is None

    def test_foreign_key_columns(self):
        ws = Workspace(name="FK Test", owner_id="user-1")
        assert hasattr(ws, "owner_id")

    def test_relationships_defined(self):
        assert hasattr(Workspace, "owner")
        assert hasattr(Workspace, "members")
        assert hasattr(Workspace, "settings")
        assert hasattr(Workspace, "projects")
        assert hasattr(Workspace, "papers")
        assert hasattr(Workspace, "citations")
        assert hasattr(Workspace, "documents")


class TestResearchProjectModel:
    def test_tablename(self):
        assert ResearchProject.__tablename__ == "research_projects"

    def test_construct(self):
        rp = ResearchProject(workspace_id="w1", name="Project A")
        assert rp.workspace_id == "w1"
        assert rp.name == "Project A"

    def test_default_values(self):
        assert ResearchProject.__table__.c.status.default.arg == "active"

    def test_uuid_generation(self):
        col = ResearchProject.__table__.c.id
        assert col.default is not None

    def test_foreign_key_columns(self):
        assert hasattr(ResearchProject, "workspace_id")

    def test_relationships_defined(self):
        assert hasattr(ResearchProject, "workspace")
        assert hasattr(ResearchProject, "sessions")
        assert hasattr(ResearchProject, "papers")

    def test_nullable_key_questions(self):
        rp = ResearchProject(workspace_id="w1", name="P")
        assert rp.key_questions is None


class TestResearchSessionModel:
    def test_tablename(self):
        assert ResearchSession.__tablename__ == "research_sessions"

    def test_construct(self):
        rs = ResearchSession(project_id="p1")
        assert rs.project_id == "p1"

    def test_default_values(self):
        assert ResearchSession.__table__.c.status.default.arg == "pending"
        assert ResearchSession.__table__.c.total_tokens.default.arg == 0
        assert ResearchSession.__table__.c.total_cost.default.arg == 0.0

    def test_uuid_generation(self):
        col = ResearchSession.__table__.c.id
        assert col.default is not None

    def test_foreign_key_columns(self):
        assert hasattr(ResearchSession, "project_id")

    def test_relationships_defined(self):
        assert hasattr(ResearchSession, "project")
        assert hasattr(ResearchSession, "documents")

    def test_nullable_fields(self):
        rs = ResearchSession(project_id="p1")
        assert rs.query is None
        assert rs.workflow_id is None
        assert rs.error_message is None

    def test_datetime_default(self):
        col = ResearchSession.__table__.c.created_at
        assert col.default is not None


class TestResearchPaperModel:
    def test_tablename(self):
        assert ResearchPaper.__tablename__ == "research_papers"

    def test_construct(self):
        rp = ResearchPaper(workspace_id="w1", title="Paper Title", source="arxiv")
        assert rp.title == "Paper Title"
        assert rp.source == "arxiv"

    def test_default_values(self):
        assert ResearchPaper.__table__.c.citation_count.default.arg == 0
        assert ResearchPaper.__table__.c.status.default.arg == "active"
        assert ResearchPaper.__table__.c.version.default.arg == 1

    def test_uuid_generation(self):
        col = ResearchPaper.__table__.c.id
        assert col.default is not None

    def test_foreign_key_columns(self):
        assert hasattr(ResearchPaper, "workspace_id")
        assert hasattr(ResearchPaper, "project_id")

    def test_relationships_defined(self):
        assert hasattr(ResearchPaper, "workspace")
        assert hasattr(ResearchPaper, "project")
        assert hasattr(ResearchPaper, "citations")

    def test_nullable_fields(self):
        rp = ResearchPaper(workspace_id="w1", title="P", source="arxiv")
        assert rp.authors is None
        assert rp.doi is None
        assert rp.arxiv_id is None


class TestCitationModel:
    def test_tablename(self):
        assert Citation.__tablename__ == "citations"

    def test_construct(self):
        c = Citation(workspace_id="w1", raw_citation_text="text", title="Paper Title")
        assert c.title == "Paper Title"
        assert c.raw_citation_text == "text"

    def test_default_values(self):
        assert Citation.__table__.c.style.default.arg == "apa"
        assert Citation.__table__.c.source_type.default.arg == "journal"

    def test_uuid_generation(self):
        col = Citation.__table__.c.id
        assert col.default is not None

    def test_foreign_key_columns(self):
        assert hasattr(Citation, "workspace_id")
        assert hasattr(Citation, "paper_id")

    def test_relationships_defined(self):
        assert hasattr(Citation, "workspace")
        assert hasattr(Citation, "paper")

    def test_nullable_fields(self):
        c = Citation(workspace_id="w1", raw_citation_text="t", title="P")
        assert c.doi is None
        assert c.isbn is None
        assert c.year is None

    def test_datetime_default(self):
        assert Citation.__table__.c.created_at.default is not None
        assert Citation.__table__.c.updated_at.default is not None


class TestDocumentModel:
    def test_tablename(self):
        assert Document.__tablename__ == "documents"

    def test_construct(self):
        d = Document(workspace_id="w1", title="Doc Title", content="content")
        assert d.title == "Doc Title"
        assert d.content == "content"

    def test_default_values(self):
        assert Document.__table__.c.format.default.arg == "markdown"
        assert Document.__table__.c.status.default.arg == "draft"
        assert Document.__table__.c.version.default.arg == 1
        assert Document.__table__.c.citation_count.default.arg == 0

    def test_uuid_generation(self):
        col = Document.__table__.c.id
        assert col.default is not None

    def test_foreign_key_columns(self):
        assert hasattr(Document, "workspace_id")
        assert hasattr(Document, "session_id")

    def test_relationships_defined(self):
        assert hasattr(Document, "workspace")
        assert hasattr(Document, "session")

    def test_nullable_fields(self):
        d = Document(workspace_id="w1", title="D", content="c")
        assert d.file_path is None
        assert d.file_size is None
        assert d.template_used is None

    def test_datetime_default(self):
        assert Document.__table__.c.created_at.default is not None
        assert Document.__table__.c.updated_at.default is not None
