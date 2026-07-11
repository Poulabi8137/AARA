from __future__ import annotations

import asyncio
import hashlib
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import AgentContext
from app.agents.registry import AgentRegistry
from app.agents.supervisor import SupervisorAgent
from app.ai.security.input_guard import InputGuard
from app.ai.security.safety_filters import SafetyFilter
from app.core.exceptions import AuthorizationError, ValidationError
from app.observability.logging import get_logger
from app.repositories import PaperRepository, ProjectRepository, SessionRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.library import PaperUpdate, PaperUploadResponse
from app.schemas.research import (
    ResearchSessionResponse,
    ResearchSubmission,
    ResearchSubmissionResponse,
)
from app.services.file_validator import validate_upload_file
from app.services.path_validator import resolve_safe_path, sanitize_filename
from app.streaming.events import EventType
from app.streaming.manager import EventStreamManager
from app.workflow.engine import WorkflowEngine
from app.workflow.types import ExecutionType, WorkflowDefinition

if TYPE_CHECKING:
    pass

STORAGE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage", "papers"
)


class ResearchService:
    # Maps SupervisorAgent's phase labels (agent_id on agent.completed events)
    # to the same session.results keys _save_phase_result already uses for
    # the manual trigger_retrieval/analysis/writing/ideas endpoints, so both
    # paths populate results identically and every tab that reads
    # session.results (Gap Analysis, Research Ideas) works regardless of
    # which path a session went through.
    _PHASE_RESULT_KEYS = {
        "Research": "research",
        "Analysis": "analysis",
        "Idea Gen": "idea_gen",
        "Writing": "writing",
    }

    def __init__(
        self,
        session_repo: SessionRepository,
        project_repo: ProjectRepository,
        workflow_engine: WorkflowEngine,
        supervisor: SupervisorAgent,
        event_manager: EventStreamManager,
        registry: AgentRegistry,
    ) -> None:
        self._session_repo = session_repo
        self._project_repo = project_repo
        self._workflow_engine = workflow_engine
        self._supervisor = supervisor
        self._event_manager = event_manager
        self._registry = registry

    async def submit_query(
        self, db: AsyncSession, user_id: str, data: ResearchSubmission
    ) -> ResearchSubmissionResponse:
        input_result = await InputGuard().validate(data.query)
        if input_result.blocked:
            raise ValidationError(f"Query rejected: {input_result.reason}", field="query")
        safety_result = await SafetyFilter().check_input(input_result.cleaned)
        if safety_result.blocked:
            raise ValidationError(f"Query rejected: {safety_result.reason}", field="query")
        data.query = input_result.cleaned

        project = await self._project_repo.get(db, data.project_id)
        from app.repositories import WorkspaceRepository

        ws_repo = WorkspaceRepository()
        workspace = await ws_repo.get(db, project.workspace_id)
        await self._verify_access(workspace, user_id, db, ws_repo)

        session = await self._session_repo.create(
            db,
            project_id=data.project_id,
            status="running",
            query=data.query,
            started_at=datetime.now(UTC),
            agent_phases_completed=[],
        )

        workflow_def = WorkflowDefinition(
            workflow_type="research",
            description=f"Research workflow for: {data.query}",
            agents=["planner", "research", "analysis", "idea_gen", "writing", "review"],
            execution_type=ExecutionType.SEQUENTIAL,
            timeout_seconds=600,
        )

        input_data = {
            "query": data.query,
            "workspace_id": project.workspace_id,
            "project_id": data.project_id,
            "session_id": session.id,
            "max_papers": data.max_papers,
            "research_direction": data.research_direction,
        }

        workflow_id = await self._workflow_engine.create_workflow(workflow_def, input_data)

        await self._session_repo.update(db, session.id, workflow_id=workflow_id)

        context = AgentContext(
            workflow_id=workflow_id,
            step_id="supervisor",
            trace_id=str(uuid4()),
            input=input_data,
        )

        # Runs in the background rather than in-request: the multi-agent pipeline
        # (planner + 5 phases, each involving LLM calls) can take up to the
        # workflow's 600s timeout, well past nginx's 300s proxy_read_timeout --
        # an in-request await here would 504 before the client ever sees a
        # response, even though the backend keeps executing regardless.
        asyncio.create_task(self._run_workflow_in_background(session.id, context))

        return ResearchSubmissionResponse(
            session_id=session.id,
            workflow_id=workflow_id,
            status="running",
            message="Research workflow started",
        )

    async def _run_workflow_in_background(self, session_id: str, context: AgentContext) -> None:
        from app.core.database import get_db_manager

        logger = get_logger("aara.research_service")
        db = None
        try:
            db = get_db_manager().create_session()
            await self._supervisor.execute(context)
            await self._persist_phase_results(db, session_id, context.workflow_id)
            await self._session_repo.update(
                db, session_id, status="completed", completed_at=datetime.now(UTC)
            )
            await db.commit()
        except Exception as exc:
            logger.error(
                "workflow_background_execution_failed",
                session_id=session_id,
                workflow_id=context.workflow_id,
                error=str(exc),
            )
            if db is not None:
                await db.rollback()
                try:
                    await self._session_repo.update(
                        db,
                        session_id,
                        status="failed",
                        completed_at=datetime.now(UTC),
                        error_message=str(exc),
                    )
                    await db.commit()
                except Exception:
                    await db.rollback()
        finally:
            if db is not None:
                await db.close()

    async def get_session(
        self, db: AsyncSession, session_id: str, user_id: str
    ) -> ResearchSessionResponse:
        session = await self._session_repo.get(db, session_id)
        project = await self._project_repo.get(db, session.project_id)
        from app.repositories import WorkspaceRepository

        ws_repo = WorkspaceRepository()
        workspace = await ws_repo.get(db, project.workspace_id)
        await self._verify_access(workspace, user_id, db, ws_repo)

        return ResearchSessionResponse(
            id=session.id,
            project_id=session.project_id,
            status=session.status,
            workflow_id=session.workflow_id,
            query=session.query or "",
            agent_phases_completed=len(session.agent_phases_completed) if session.agent_phases_completed else 0,
            total_tokens=session.total_tokens,
            total_cost=session.total_cost,
            started_at=session.started_at,
            completed_at=session.completed_at,
            error_message=session.error_message,
            created_at=session.created_at,
        )

    async def list_sessions(
        self,
        db: AsyncSession,
        project_id: str | None,
        user_id: str,
        skip: int,
        limit: int,
    ) -> tuple[list[ResearchSessionResponse], int]:
        if project_id is not None:
            project = await self._project_repo.get(db, project_id)
            from app.repositories import WorkspaceRepository

            ws_repo = WorkspaceRepository()
            workspace = await ws_repo.get(db, project.workspace_id)
            await self._verify_access(workspace, user_id, db, ws_repo)

            sessions = await self._session_repo.get_by_project(db, project_id, skip=skip, limit=limit)
            total = len(await self._session_repo.get_by_project(db, project_id))
        else:
            # No project_id given: list sessions across every project the user
            # can access (owner or workspace member), newest first.
            projects = await self._get_user_projects(db, user_id)
            all_sessions = await self._session_repo.get_by_project_ids(
                db, [p.id for p in projects], limit=10000
            )
            all_sessions.sort(key=lambda s: s.created_at, reverse=True)
            total = len(all_sessions)
            sessions = all_sessions[skip : skip + limit]

        results = [
            ResearchSessionResponse(
                id=s.id,
                project_id=s.project_id,
                status=s.status,
                workflow_id=s.workflow_id,
                query=s.query or "",
                agent_phases_completed=len(s.agent_phases_completed) if s.agent_phases_completed else 0,
                total_tokens=s.total_tokens,
                total_cost=s.total_cost,
                started_at=s.started_at,
                completed_at=s.completed_at,
                error_message=s.error_message,
                created_at=s.created_at,
            )
            for s in sessions
        ]

        return results, total

    async def upload_paper(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        file: Any,
        metadata: PaperUpdate | None = None,
    ) -> PaperUploadResponse:
        validate_upload_file(file)
        from app.repositories import WorkspaceRepository

        ws_repo = WorkspaceRepository()
        workspace = await ws_repo.get(db, workspace_id)
        await self._verify_access(workspace, user_id, db, ws_repo)

        content = await file.read() if hasattr(file, "read") else file
        content_hash = hashlib.sha256(content if isinstance(content, bytes) else content.encode()).hexdigest()

        os.makedirs(STORAGE_DIR, exist_ok=True)
        raw_name = sanitize_filename(getattr(file, "filename", "unknown.pdf") or "unknown.pdf")
        file_ext = raw_name.split(".")[-1] if "." in raw_name else "pdf"
        file_path = os.path.join(STORAGE_DIR, f"{uuid4().hex}.{file_ext}")
        resolve_safe_path(STORAGE_DIR, file_path)

        with open(file_path, "wb") as f:
            f.write(content if isinstance(content, bytes) else content.encode())

        paper_repo = PaperRepository()
        paper = await paper_repo.create(
            db,
            workspace_id=workspace_id,
            title=metadata.title if metadata and metadata.title else getattr(file, "filename", "Untitled"),
            source="upload",
            file_path=file_path,
            file_type=file_ext,
            file_size=len(content) if isinstance(content, bytes) else len(content.encode()),
            content_hash=content_hash,
            doi=metadata.doi if metadata else None,
            authors=metadata.authors if metadata else None,
            abstract=metadata.abstract if metadata else None,
        )

        return PaperUploadResponse(
            id=paper.id,
            title=paper.title,
            file_type=paper.file_type or "",
            file_size=paper.file_size,
            status=paper.status,
            version=paper.version,
            created_at=paper.created_at,
        )

    async def trigger_retrieval(
        self, db: AsyncSession, session_id: str, user_id: str
    ) -> ResearchSessionResponse:
        session = await self._session_repo.get(db, session_id)
        project = await self._project_repo.get(db, session.project_id)
        from app.repositories import WorkspaceRepository

        ws_repo = WorkspaceRepository()
        workspace = await ws_repo.get(db, project.workspace_id)
        await self._verify_access(workspace, user_id, db, ws_repo)

        workflow_id = session.workflow_id or f"wf_{uuid4().hex[:12]}"
        context = AgentContext(
            workflow_id=workflow_id,
            step_id="research",
            trace_id=str(uuid4()),
            input={"query": session.query, "workspace_id": project.workspace_id},
        )
        agent = self._registry.get("research")
        output = await agent.execute(context)
        await self._save_phase_result(db, session_id, "research", output.output)

        return await self.get_session(db, session_id, user_id)

    async def trigger_analysis(
        self, db: AsyncSession, session_id: str, user_id: str
    ) -> ResearchSessionResponse:
        session = await self._session_repo.get(db, session_id)
        project = await self._project_repo.get(db, session.project_id)
        from app.repositories import WorkspaceRepository

        ws_repo = WorkspaceRepository()
        workspace = await ws_repo.get(db, project.workspace_id)
        await self._verify_access(workspace, user_id, db, ws_repo)

        workflow_id = session.workflow_id or f"wf_{uuid4().hex[:12]}"
        # Feed the paper collection retrieval already gathered — previously
        # this input never included "papers"/"paper_collection" at all, so
        # AnalysisAgent silently ran on an empty list and always produced
        # zero gaps/themes regardless of what retrieval actually found.
        prior_results = session.results or {}
        paper_collection = prior_results.get("research", {}).get("paper_collection", {})
        context = AgentContext(
            workflow_id=workflow_id,
            step_id="analysis",
            trace_id=str(uuid4()),
            input={
                "query": session.query,
                "workspace_id": project.workspace_id,
                "paper_collection": paper_collection,
            },
        )
        agent = self._registry.get("analysis")
        output = await agent.execute(context)
        await self._save_phase_result(db, session_id, "analysis", output.output)

        return await self.get_session(db, session_id, user_id)

    async def trigger_writing(
        self, db: AsyncSession, session_id: str, user_id: str
    ) -> ResearchSessionResponse:
        session = await self._session_repo.get(db, session_id)
        project = await self._project_repo.get(db, session.project_id)
        from app.repositories import WorkspaceRepository

        ws_repo = WorkspaceRepository()
        workspace = await ws_repo.get(db, project.workspace_id)
        await self._verify_access(workspace, user_id, db, ws_repo)

        workflow_id = session.workflow_id or f"wf_{uuid4().hex[:12]}"
        prior_results = session.results or {}
        analysis_report = prior_results.get("analysis", {}).get("analysis_report", {})
        papers = prior_results.get("research", {}).get("paper_collection", {}).get("papers", [])
        context = AgentContext(
            workflow_id=workflow_id,
            step_id="writing",
            trace_id=str(uuid4()),
            input={
                "query": session.query,
                "workspace_id": project.workspace_id,
                "analysis_report": analysis_report,
                "papers": papers,
            },
        )
        agent = self._registry.get("writing")
        output = await agent.execute(context)
        await self._save_phase_result(db, session_id, "writing", output.output)

        return await self.get_session(db, session_id, user_id)

    async def trigger_ideas(
        self, db: AsyncSession, session_id: str, user_id: str
    ) -> ResearchSessionResponse:
        session = await self._session_repo.get(db, session_id)
        project = await self._project_repo.get(db, session.project_id)
        from app.repositories import WorkspaceRepository

        ws_repo = WorkspaceRepository()
        workspace = await ws_repo.get(db, project.workspace_id)
        await self._verify_access(workspace, user_id, db, ws_repo)

        workflow_id = session.workflow_id or f"wf_{uuid4().hex[:12]}"
        prior_results = session.results or {}
        analysis_report = prior_results.get("analysis", {}).get("analysis_report", {})
        papers = prior_results.get("research", {}).get("paper_collection", {}).get("papers", [])
        # IdeaGenerationAgent reads analysis_report["research_gaps"] with each
        # gap needing "id"/"area" — AnalysisAgent's own vocabulary is
        # "gaps"/"theme" (see AnalysisAgent.detect_gaps). Same class of
        # phase-vocabulary mismatch as the one already fixed in supervisor.py
        # for evaluation phase names; remapped here rather than renaming
        # either agent's public output shape.
        research_gaps = [
            {**gap, "id": gap.get("theme", ""), "area": gap.get("theme", "")}
            for gap in analysis_report.get("gaps", [])
        ]
        context = AgentContext(
            workflow_id=workflow_id,
            step_id="ideas",
            trace_id=str(uuid4()),
            input={
                "query": session.query,
                "workspace_id": project.workspace_id,
                "analysis_report": {**analysis_report, "research_gaps": research_gaps, "papers": papers},
            },
        )
        agent = self._registry.get("idea_gen")
        output = await agent.execute(context)
        await self._save_phase_result(db, session_id, "idea_gen", output.output)

        return await self.get_session(db, session_id, user_id)

    async def _save_phase_result(
        self, db: AsyncSession, session_id: str, phase: str, output: dict
    ) -> None:
        session = await self._session_repo.get(db, session_id)
        merged = {**(session.results or {}), phase: output}
        await self._session_repo.update(db, session_id, results=merged)

    async def _persist_phase_results(
        self, db: AsyncSession, session_id: str, workflow_id: str | None
    ) -> None:
        # The automatic pipeline (submit_query -> SupervisorAgent.execute)
        # never called _save_phase_result itself -- only the manual
        # trigger_retrieval/analysis/writing/ideas endpoints did. Backfills
        # session.results from the same agent.completed events the SSE
        # stream already carries, so sessions started via the automatic
        # path get real Gap Analysis / Research Ideas output too, not an
        # empty "run analysis" prompt despite the phase having already run.
        if not workflow_id:
            return
        events = await self._event_manager.get_event_history(workflow_id)
        for event in events:
            if event.type != EventType.AGENT_COMPLETED:
                continue
            phase_key = self._PHASE_RESULT_KEYS.get(getattr(event, "agent_id", None))
            result = (event.data or {}).get("result")
            if phase_key and result:
                await self._save_phase_result(db, session_id, phase_key, result)

    async def _verify_access(
        self, workspace: Any, user_id: str, db: AsyncSession, ws_repo: WorkspaceRepository
    ) -> None:
        if workspace.owner_id == user_id:
            return
        role = await ws_repo.get_member_role(db, workspace.id, user_id)
        if role is None:
            raise AuthorizationError("User does not have access to this workspace")

    async def _get_user_projects(
        self, db: AsyncSession, user_id: str
    ) -> list[Any]:
        workspaces = await WorkspaceRepository().get_for_user(db, user_id, limit=100)
        workspace_ids = [w.id for w in workspaces]
        return await self._project_repo.get_by_workspace_ids(db, workspace_ids)

    async def get_overview(self, db: AsyncSession, user_id: str) -> dict:
        workspaces = await WorkspaceRepository().get_for_user(db, user_id, limit=100)
        workspace_ids = [w.id for w in workspaces]

        projects = await self._project_repo.get_by_workspace_ids(db, workspace_ids)
        papers = await PaperRepository().get_by_workspace_ids(db, workspace_ids)

        active_projects = [p for p in projects if p.status == "active"]
        archived_projects = [p for p in projects if p.status == "archived"]

        active_project_ids = [p.id for p in active_projects]
        sessions = await self._session_repo.get_by_project_ids(db, active_project_ids)
        sessions_by_project: dict[str, list[Any]] = {}
        for s in sessions:
            sessions_by_project.setdefault(s.project_id, []).append(s)

        in_progress = 0
        stale = 0
        for project in active_projects:
            project_sessions = sessions_by_project.get(project.id, [])
            if any(s.status in ("running", "pending") for s in project_sessions):
                in_progress += 1
            elif not project_sessions:
                stale += 1

        return {
            "projects": len(projects),
            "papers": len(papers),
            "notes": 0,
            "ideas": 0,
            "activeProjects": len(active_projects),
            "completedProjects": len(archived_projects),
            "inProgressProjects": in_progress,
            "staleProjects": stale,
        }

    async def get_activity(self, db: AsyncSession, user_id: str) -> dict:
        projects = await self._get_user_projects(db, user_id)
        recent = sorted(projects, key=lambda p: p.updated_at, reverse=True)[:5]
        return {
            "recentlyOpened": [
                {
                    "id": p.id,
                    "title": p.name,
                    "lastAccessed": p.updated_at.isoformat() if p.updated_at else None,
                    "status": p.status,
                }
                for p in recent
            ]
        }

    async def get_cards(self, db: AsyncSession, user_id: str) -> list[dict]:
        projects = await self._get_user_projects(db, user_id)
        active_projects = sorted(
            (p for p in projects if p.status == "active"),
            key=lambda p: p.updated_at,
            reverse=True,
        )
        return [
            {
                "id": p.id,
                "type": "project",
                "title": p.name,
                "description": p.description or p.research_goal or "",
                "date": p.updated_at.isoformat() if p.updated_at else None,
                "status": "active",
            }
            for p in active_projects[:12]
        ]

    async def get_recent_activity(self, db: AsyncSession, user_id: str) -> list[dict]:
        workspaces = await WorkspaceRepository().get_for_user(db, user_id, limit=100)
        workspace_ids = [w.id for w in workspaces]
        events: list[dict] = []

        sessions = await self._session_repo.get_recent_by_workspace_ids(db, workspace_ids, limit=20)
        for s in sessions:
            events.append({
                "id": s.id,
                "type": "task",
                "title": s.query or "Research session",
                "timestamp": s.created_at.isoformat() if s.created_at else None,
                "status": "completed" if s.status == "completed" else "created",
                "project_id": s.project_id,
            })

        papers = await PaperRepository().get_by_workspace_ids(db, workspace_ids)
        for p in papers[:20]:
            events.append({
                "id": p.id,
                "type": "paper",
                "title": p.title,
                "timestamp": p.created_at.isoformat() if p.created_at else None,
                "status": "imported",
                "project_id": p.project_id,
            })

        events.sort(key=lambda e: e["timestamp"] or "", reverse=True)
        return events[:20]

    async def get_notes(self, db: AsyncSession, user_id: str) -> list[dict]:
        # Notes are not yet a modeled feature; report an honest empty list.
        return []

    async def get_reading_queue(self, db: AsyncSession, user_id: str) -> list[dict]:
        # Reading-queue is not yet a modeled feature; report an honest empty list.
        return []

    async def get_saved_papers(self, db: AsyncSession, user_id: str) -> list[dict]:
        # Saved-papers is not yet a modeled feature; report an honest empty list.
        return []
