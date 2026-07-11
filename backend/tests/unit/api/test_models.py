from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.citation import (
    CitationCreate,
    CitationExportRequest,
    CitationExportResponse,
    CitationLibrarySummary,
    CitationResponse,
    CitationUpdate,
)
from app.schemas.dashboard import (
    DashboardResponse,
    EvaluationScoreResponse,
    ProviderUsageResponse,
    TokenUsageResponse,
    WorkflowStatusResponse,
)
from app.schemas.document import (
    DocumentExportRequest,
    DocumentGenerateRequest,
    DocumentResponse,
)
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


class TestResearchSchemas:
    def test_research_project_create_defaults(self):
        s = ResearchProjectCreate(workspace_id="ws-1", name="My Project")
        assert s.workspace_id == "ws-1"
        assert s.name == "My Project"
        assert s.description is None
        assert s.research_goal is None
        assert s.key_questions is None

    def test_research_project_create_custom(self):
        s = ResearchProjectCreate(
            workspace_id="ws-1",
            name="Advanced Research",
            description="desc",
            research_goal="goal",
            key_questions=["q1", "q2"],
        )
        assert s.key_questions == ["q1", "q2"]

    def test_research_project_create_name_min_length(self):
        with pytest.raises(ValidationError):
            ResearchProjectCreate(workspace_id="ws-1", name="")

    def test_research_project_create_name_max_length(self):
        with pytest.raises(ValidationError):
            ResearchProjectCreate(workspace_id="ws-1", name="x" * 256)

    def test_research_project_update_defaults(self):
        s = ResearchProjectUpdate()
        assert s.name is None
        assert s.status is None

    def test_research_project_update_custom(self):
        s = ResearchProjectUpdate(name="Updated", status="archived")
        assert s.name == "Updated"
        assert s.status == "archived"

    def test_research_project_update_invalid_status(self):
        with pytest.raises(ValidationError):
            ResearchProjectUpdate(status="deleted")

    def test_research_project_response_defaults(self):
        s = ResearchProjectResponse(id="p1", workspace_id="ws-1", name="P")
        assert s.status == "active"
        assert s.session_count == 0
        assert s.paper_count == 0
        assert s.description is None

    def test_research_project_response_custom(self):
        s = ResearchProjectResponse(
            id="p1",
            workspace_id="ws-1",
            name="P",
            status="archived",
            session_count=5,
            paper_count=3,
        )
        assert s.session_count == 5
        assert s.paper_count == 3

    def test_research_project_response_from_attributes(self):
        data = {
            "id": "p1",
            "workspace_id": "ws-1",
            "name": "From DB",
            "status": "active",
            "session_count": 0,
            "paper_count": 0,
        }
        s = ResearchProjectResponse.model_validate(data)
        assert s.name == "From DB"

    def test_research_project_response_serialization(self):
        s = ResearchProjectResponse(id="p1", workspace_id="ws-1", name="P")
        d = s.model_dump()
        assert d["id"] == "p1"
        assert d["status"] == "active"

    def test_research_session_create(self):
        s = ResearchSessionCreate(project_id="p1", query="test query")
        assert s.project_id == "p1"
        assert s.query == "test query"

    def test_research_session_response_defaults(self):
        s = ResearchSessionResponse(
            id="s1", project_id="p1", status="pending", query="q"
        )
        assert s.agent_phases_completed == 0
        assert s.total_tokens == 0
        assert s.total_cost == 0.0
        assert s.workflow_id is None

    def test_research_session_response_custom(self):
        s = ResearchSessionResponse(
            id="s1",
            project_id="p1",
            status="running",
            query="q",
            total_tokens=1000,
            total_cost=0.05,
            workflow_id="wf-1",
        )
        assert s.total_tokens == 1000
        assert s.total_cost == 0.05

    def test_research_session_response_from_attributes(self):
        data = {
            "id": "s1",
            "project_id": "p1",
            "status": "completed",
            "query": "q",
        }
        s = ResearchSessionResponse.model_validate(data)
        assert s.status == "completed"

    def test_research_submission_defaults(self):
        s = ResearchSubmission(query="q", project_id="p1")
        assert s.max_papers == 50
        assert s.research_direction is None

    def test_research_submission_custom(self):
        s = ResearchSubmission(
            query="q", project_id="p1", max_papers=100, research_direction="dir"
        )
        assert s.max_papers == 100

    def test_research_submission_response(self):
        s = ResearchSubmissionResponse(
            session_id="s1", workflow_id="wf-1", status="started", message="ok"
        )
        assert s.session_id == "s1"
        assert s.message == "ok"


class TestCitationSchemas:
    def test_citation_create_defaults(self):
        s = CitationCreate(title="My Paper")
        assert s.style == "apa"
        assert s.source_type == "journal"
        assert s.paper_id is None
        assert s.year is None

    def test_citation_create_custom(self):
        s = CitationCreate(
            title="Paper",
            style="mla",
            source_type="book",
            year=2024,
            authors=["A"],
            doi="10.1234/abc",
        )
        assert s.style == "mla"
        assert s.source_type == "book"
        assert s.authors == ["A"]

    def test_citation_create_required_title(self):
        with pytest.raises(ValidationError):
            CitationCreate()

    def test_citation_update_defaults(self):
        s = CitationUpdate()
        assert s.title is None
        assert s.style is None

    def test_citation_update_custom(self):
        s = CitationUpdate(title="Updated", year=2025)
        assert s.title == "Updated"
        assert s.year == 2025

    def test_citation_response_defaults(self):
        s = CitationResponse(id="c1", workspace_id="ws-1", title="T")
        assert s.style == "apa"
        assert s.source_type == "journal"
        assert s.year is None

    def test_citation_response_custom(self):
        s = CitationResponse(
            id="c1",
            workspace_id="ws-1",
            title="T",
            style="ieee",
            year=2023,
            doi="10.1234/xyz",
        )
        assert s.style == "ieee"
        assert s.doi == "10.1234/xyz"

    def test_citation_response_from_attributes(self):
        data = {
            "id": "c1",
            "workspace_id": "ws-1",
            "title": "From DB",
            "style": "apa",
            "source_type": "journal",
        }
        s = CitationResponse.model_validate(data)
        assert s.title == "From DB"

    def test_citation_export_request(self):
        s = CitationExportRequest(
            citation_ids=["c1", "c2"], format="bibtex"
        )
        assert s.citation_ids == ["c1", "c2"]
        assert s.format == "bibtex"

    def test_citation_export_request_invalid_format(self):
        with pytest.raises(ValidationError):
            CitationExportRequest(citation_ids=[], format="invalid")

    def test_citation_export_response(self):
        s = CitationExportResponse(
            format="ris", content="some text", filename="refs.ris"
        )
        assert s.content == "some text"

    def test_citation_library_summary(self):
        s = CitationLibrarySummary(
            total_citations=10,
            by_style={"apa": 5, "mla": 5},
            by_source_type={"journal": 8, "book": 2},
        )
        assert s.total_citations == 10
        assert s.by_style["apa"] == 5


class TestLibrarySchemas:
    def test_paper_upload_response_defaults(self):
        s = PaperUploadResponse(
            id="p1", title="Paper", file_type="pdf", status="active"
        )
        assert s.version == 1
        assert s.file_size is None

    def test_paper_upload_response_custom(self):
        s = PaperUploadResponse(
            id="p1",
            title="Paper",
            file_type="pdf",
            status="active",
            file_size=1024,
            version=2,
        )
        assert s.file_size == 1024
        assert s.version == 2

    def test_paper_upload_response_from_attributes(self):
        data = {
            "id": "p1",
            "title": "Paper",
            "file_type": "pdf",
            "status": "active",
            "version": 1,
        }
        s = PaperUploadResponse.model_validate(data)
        assert s.title == "Paper"

    def test_paper_update_defaults(self):
        s = PaperUpdate()
        assert s.title is None
        assert s.authors is None

    def test_paper_update_custom(self):
        s = PaperUpdate(
            title="New Title",
            authors=["Alice", "Bob"],
            doi="10.1234/paper",
            publication_year=2024,
        )
        assert s.authors == ["Alice", "Bob"]
        assert s.doi == "10.1234/paper"

    def test_paper_response_defaults(self):
        s = PaperResponse(id="p1", workspace_id="ws-1", title="T")
        assert s.citation_count == 0
        assert s.version == 1
        assert s.source is None
        assert s.project_id is None

    def test_paper_response_custom(self):
        s = PaperResponse(
            id="p1",
            workspace_id="ws-1",
            title="T",
            source="arxiv",
            citation_count=15,
            version=3,
        )
        assert s.citation_count == 15
        assert s.source == "arxiv"

    def test_paper_response_from_attributes(self):
        data = {
            "id": "p1",
            "workspace_id": "ws-1",
            "title": "From DB",
            "citation_count": 0,
            "version": 1,
        }
        s = PaperResponse.model_validate(data)
        assert s.title == "From DB"

    def test_paper_version_response_defaults(self):
        s = PaperVersionResponse(version=1)
        assert s.file_type is None
        assert s.file_size is None
        assert s.created_at is None

    def test_paper_version_response_custom(self):
        t = datetime.now(UTC)
        s = PaperVersionResponse(version=2, file_type="pdf", file_size=500, created_at=t)
        assert s.file_type == "pdf"
        assert s.file_size == 500
        assert s.created_at == t

    def test_duplicate_check_response(self):
        s = DuplicateCheckResponse(is_duplicate=True, confidence=0.95)
        assert s.is_duplicate is True
        assert s.confidence == 0.95
        assert s.existing_paper is None

    def test_duplicate_check_response_with_paper(self):
        p = PaperResponse(id="p1", workspace_id="ws-1", title="Existing")
        s = DuplicateCheckResponse(
            is_duplicate=True, existing_paper=p, confidence=0.98
        )
        assert s.existing_paper is not None
        assert s.existing_paper.title == "Existing"


class TestDocumentSchemas:
    def test_document_generate_request_defaults(self):
        s = DocumentGenerateRequest(
            workspace_id="ws-1", format="markdown", title="Doc"
        )
        assert s.session_id is None
        assert s.project_id is None
        assert s.template is None
        assert s.sections is None

    def test_document_generate_request_custom(self):
        s = DocumentGenerateRequest(
            workspace_id="ws-1",
            session_id="s1",
            format="pdf",
            title="Report",
            template="default",
            sections=["intro", "conclusion"],
        )
        assert s.format == "pdf"
        assert s.sections == ["intro", "conclusion"]

    def test_document_generate_request_invalid_format(self):
        with pytest.raises(ValidationError):
            DocumentGenerateRequest(
                workspace_id="ws-1", format="doc", title="T"
            )

    def test_document_response_defaults(self):
        s = DocumentResponse(
            id="d1", workspace_id="ws-1", format="md", title="T", status="draft"
        )
        assert s.version == 1
        assert s.citation_count == 0
        assert s.content is None

    def test_document_response_custom(self):
        s = DocumentResponse(
            id="d1",
            workspace_id="ws-1",
            format="markdown",
            title="Doc",
            status="final",
            version=3,
            citation_count=10,
            content="# Hello",
        )
        assert s.content == "# Hello"
        assert s.citation_count == 10

    def test_document_response_from_attributes(self):
        data = {
            "id": "d1",
            "workspace_id": "ws-1",
            "format": "markdown",
            "title": "From DB",
            "status": "draft",
            "version": 1,
            "citation_count": 0,
        }
        s = DocumentResponse.model_validate(data)
        assert s.title == "From DB"

    def test_document_export_request(self):
        s = DocumentExportRequest(format="html")
        assert s.format == "html"

    def test_document_export_request_invalid_format(self):
        with pytest.raises(ValidationError):
            DocumentExportRequest(format="txt")


class TestDashboardSchemas:
    def test_workflow_status_response_defaults(self):
        s = WorkflowStatusResponse(
            workflow_id="wf-1", status="running", progress_pct=0.0, elapsed_seconds=0.0
        )
        assert s.current_phase is None
        assert s.current_agent is None
        assert s.started_at is None

    def test_workflow_status_response_custom(self):
        t = datetime.now(UTC)
        s = WorkflowStatusResponse(
            workflow_id="wf-1",
            status="completed",
            current_phase="review",
            current_agent="reviewer",
            progress_pct=100.0,
            started_at=t,
            completed_at=t,
            elapsed_seconds=120.5,
        )
        assert s.current_phase == "review"
        assert s.progress_pct == 100.0
        assert s.elapsed_seconds == 120.5

    def test_token_usage_response(self):
        s = TokenUsageResponse(
            total_tokens=5000, prompt_tokens=3000, completion_tokens=2000, estimated_cost=0.15
        )
        assert s.total_tokens == 5000
        assert s.completion_tokens == 2000
        assert s.estimated_cost == 0.15

    def test_provider_usage_response(self):
        s = ProviderUsageResponse(
            provider="openai", model="gpt-4", calls=10, tokens=5000, cost=0.5
        )
        assert s.calls == 10
        assert s.cost == 0.5

    def test_evaluation_score_response_defaults(self):
        s = EvaluationScoreResponse(metric="accuracy", score=0.95)
        assert s.details is None

    def test_evaluation_score_response_custom(self):
        s = EvaluationScoreResponse(
            metric="f1", score=0.88, details={"threshold": 0.5}
        )
        assert s.details == {"threshold": 0.5}

    def test_dashboard_response(self):
        wf = WorkflowStatusResponse(
            workflow_id="wf-1", status="done", progress_pct=100.0, elapsed_seconds=10.0
        )
        tok = TokenUsageResponse(
            total_tokens=100, prompt_tokens=60, completion_tokens=40, estimated_cost=0.01
        )
        prov = [
            ProviderUsageResponse(
                provider="openai", model="gpt-4", calls=2, tokens=100, cost=0.01
            )
        ]
        evals = [
            EvaluationScoreResponse(metric="accuracy", score=0.95)
        ]
        s = DashboardResponse(
            workflow=wf,
            tokens=tok,
            providers=prov,
            evaluation_scores=evals,
            timeline=[{"step": "start", "ts": "2024-01-01"}],
        )
        assert s.workflow.status == "done"
        assert s.tokens.total_tokens == 100
        assert len(s.providers) == 1
        assert len(s.evaluation_scores) == 1
        assert s.timeline[0]["step"] == "start"


class TestSearchSchemas:
    def test_search_request_defaults(self):
        s = SearchRequest(query="test", scope="workspace")
        assert s.page == 1
        assert s.page_size == 20
        assert s.workspace_id is None
        assert s.project_id is None
        assert s.filters is None

    def test_search_request_custom(self):
        s = SearchRequest(
            query="test",
            scope="papers",
            workspace_id="ws-1",
            project_id="p1",
            page=2,
            page_size=50,
            filters={"year": 2024},
        )
        assert s.page == 2
        assert s.page_size == 50
        assert s.filters == {"year": 2024}

    def test_search_request_page_ge_1(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="test", scope="workspace", page=0)

    def test_search_request_page_size_le_100(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="test", scope="workspace", page_size=101)

    def test_search_request_invalid_scope(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="test", scope="invalid")

    def test_search_result_defaults(self):
        s = SearchResult(
            id="r1", type="paper", title="Result", snippet="...", score=0.95
        )
        assert s.metadata == {}

    def test_search_result_custom(self):
        s = SearchResult(
            id="r1",
            type="citation",
            title="Ref",
            snippet="cited",
            score=0.85,
            metadata={"year": 2023},
        )
        assert s.metadata == {"year": 2023}

    def test_search_result_invalid_type(self):
        with pytest.raises(ValidationError):
            SearchResult(id="r1", type="unknown", title="T", snippet="s", score=0.5)

    def test_search_response(self):
        results = [
            SearchResult(id="r1", type="paper", title="T1", snippet="s1", score=0.9)
        ]
        s = SearchResponse(results=results, total=1, page=1, page_size=20, total_pages=1)
        assert len(s.results) == 1
        assert s.total == 1
        assert s.total_pages == 1
