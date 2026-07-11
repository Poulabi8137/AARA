from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.repositories.citation_repository import CitationRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.paper_repository import PaperRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.dashboard import (
    DashboardResponse,
    EvaluationScoreResponse,
    ProviderUsageResponse,
    TokenUsageResponse,
    WorkflowStatusResponse,
)
from app.agents.supervisor import SupervisorAgent
from app.streaming.events import BaseEvent, EventType
from app.streaming.manager import EventStreamManager
from app.workflow.types import WorkflowStatus


class DashboardService:
    def __init__(
        self,
        event_manager: EventStreamManager,
        session_repo: SessionRepository,
        project_repo: ProjectRepository,
        workspace_repo: WorkspaceRepository,
        paper_repo: PaperRepository,
        citation_repo: CitationRepository,
        conversation_repo: ConversationRepository,
    ) -> None:
        self._event_manager = event_manager
        self._session_repo = session_repo
        self._project_repo = project_repo
        self._workspace_repo = workspace_repo
        self._paper_repo = paper_repo
        self._citation_repo = citation_repo
        self._conversation_repo = conversation_repo

    async def _verify_workspace_access(
        self, db: AsyncSession, workspace_id: str, user_id: str
    ) -> None:
        workspace = await self._workspace_repo.get(db, workspace_id)
        if workspace.owner_id == user_id:
            return
        role = await self._workspace_repo.get_member_role(db, workspace_id, user_id)
        if role is None:
            raise AuthorizationError("User does not have access to this workspace")

    async def _verify_workflow_access(
        self, db: AsyncSession, workflow_id: str, user_id: str
    ):
        session = await self._session_repo.get_by_workflow_id(db, workflow_id)
        if session is None:
            raise NotFoundError("Workflow", workflow_id)
        project = await self._project_repo.get(db, session.project_id)
        await self._verify_workspace_access(db, project.workspace_id, user_id)
        return session

    async def get_workflow_status(
        self, db: AsyncSession, workflow_id: str, user_id: str
    ) -> WorkflowStatusResponse:
        session = await self._verify_workflow_access(db, workflow_id, user_id)
        return await self._get_workflow_status(workflow_id, session)

    async def _get_workflow_status(self, workflow_id: str, session) -> WorkflowStatusResponse:
        # Status/timestamps come from the DB session row rather than
        # WorkflowEngine, which is a single process-wide singleton whose
        # in-memory state belongs to whichever workflow was created most
        # recently -- not necessarily this workflow_id.
        status = session.status or WorkflowStatus.PENDING.value
        started_at = session.started_at
        now = datetime.now(UTC)

        events = await self._event_manager.get_event_history(workflow_id)

        completed_at = session.completed_at
        current_phase = None
        for event in reversed(events):
            if current_phase is None and event.type in (
                EventType.AGENT_STARTED,
                EventType.AGENT_COMPLETED,
            ):
                current_phase = getattr(event, "agent_id", None)
            if completed_at is None and event.type in (
                EventType.WORKFLOW_COMPLETED,
                EventType.WORKFLOW_FAILED,
                EventType.WORKFLOW_CANCELLED,
            ):
                completed_at = event.timestamp
            if current_phase is not None and completed_at is not None:
                break

        elapsed = 0.0
        if started_at:
            end = completed_at or now
            elapsed = (end - started_at).total_seconds()

        total_phases = len(SupervisorAgent.ALL_PHASES)
        completed_phases = len({
            getattr(e, "agent_id", None) for e in events if e.type == EventType.AGENT_COMPLETED
        })
        progress_pct = (completed_phases / total_phases * 100) if total_phases else 0.0
        if status == "completed":
            progress_pct = 100.0

        return WorkflowStatusResponse(
            workflow_id=workflow_id,
            status=status,
            current_phase=current_phase,
            current_agent=current_phase,
            progress_pct=progress_pct,
            started_at=started_at,
            completed_at=completed_at,
            elapsed_seconds=elapsed,
        )

    async def verify_workflow_access(
        self, db: AsyncSession, workflow_id: str, user_id: str
    ) -> None:
        await self._verify_workflow_access(db, workflow_id, user_id)

    def stream_events(self, workflow_id: str) -> AsyncGenerator[BaseEvent, None]:
        return self._event_manager.stream_events(workflow_id)

    async def get_token_usage(
        self, db: AsyncSession, workflow_id: str, user_id: str
    ) -> TokenUsageResponse:
        await self._verify_workflow_access(db, workflow_id, user_id)
        return await self._get_token_usage(workflow_id)

    async def _get_token_usage(self, workflow_id: str) -> TokenUsageResponse:
        events = await self._event_manager.get_event_history(workflow_id)

        total_tokens = 0
        prompt_tokens = 0
        completion_tokens = 0
        estimated_cost = 0.0

        for event in events:
            data = event.data or {}
            if "token_usage" in data:
                tu = data["token_usage"]
                total_tokens += tu.get("total_tokens", 0)
                prompt_tokens += tu.get("prompt_tokens", 0)
                completion_tokens += tu.get("completion_tokens", 0)
                estimated_cost += tu.get("cost", 0.0)

        return TokenUsageResponse(
            total_tokens=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost=estimated_cost,
        )

    async def get_provider_usage(
        self, db: AsyncSession, workflow_id: str, user_id: str
    ) -> list[ProviderUsageResponse]:
        await self._verify_workflow_access(db, workflow_id, user_id)
        return await self._get_provider_usage(workflow_id)

    async def _get_provider_usage(
        self, workflow_id: str
    ) -> list[ProviderUsageResponse]:
        events = await self._event_manager.get_event_history(workflow_id)

        provider_map: dict[str, dict[str, Any]] = {}

        for event in events:
            data = event.data or {}
            if "provider_call" in data:
                call = data["provider_call"]
                pid = call.get("provider", "unknown")
                model = call.get("model", "unknown")
                key = f"{pid}:{model}"

                if key not in provider_map:
                    provider_map[key] = {
                        "provider": pid,
                        "model": model,
                        "calls": 0,
                        "tokens": 0,
                        "cost": 0.0,
                    }

                provider_map[key]["calls"] += 1
                provider_map[key]["tokens"] += call.get("tokens", 0)
                provider_map[key]["cost"] += call.get("cost", 0.0)

        return [
            ProviderUsageResponse(**v) for v in provider_map.values()
        ]

    async def get_evaluation_scores(
        self, db: AsyncSession, workflow_id: str, user_id: str
    ) -> list[EvaluationScoreResponse]:
        await self._verify_workflow_access(db, workflow_id, user_id)
        return await self._get_evaluation_scores(workflow_id)

    async def _get_evaluation_scores(
        self, workflow_id: str
    ) -> list[EvaluationScoreResponse]:
        events = await self._event_manager.get_event_history(workflow_id)
        scores = []

        for event in events:
            data = event.data or {}
            if "evaluation" in data:
                eval_data = data["evaluation"]
                scores.append(
                    EvaluationScoreResponse(
                        metric=eval_data.get("metric", "unknown"),
                        score=eval_data.get("score", 0.0),
                        details=eval_data.get("details"),
                    )
                )

        return scores

    async def get_full_dashboard(
        self, db: AsyncSession, workflow_id: str, user_id: str
    ) -> DashboardResponse:
        session = await self._verify_workflow_access(db, workflow_id, user_id)

        status = await self._get_workflow_status(workflow_id, session)
        tokens = await self._get_token_usage(workflow_id)
        providers = await self._get_provider_usage(workflow_id)
        scores = await self._get_evaluation_scores(workflow_id)
        timeline = await self._get_workflow_timeline(workflow_id)

        return DashboardResponse(
            workflow=status,
            tokens=tokens,
            providers=providers,
            evaluation_scores=scores,
            timeline=timeline,
        )

    async def get_event_timeline(
        self, db: AsyncSession, workflow_id: str, user_id: str
    ) -> list[dict]:
        await self._verify_workflow_access(db, workflow_id, user_id)
        return await self._get_workflow_timeline(workflow_id)

    async def _get_workflow_timeline(self, workflow_id: str) -> list[dict]:
        events = await self._event_manager.get_event_history(workflow_id)

        timeline = []
        for event in events:
            timeline.append({
                "event_id": event.event_id,
                "type": event.type.value if hasattr(event.type, "value") else str(event.type),
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "data": event.data,
                "agent_id": getattr(event, "agent_id", None),
                "status": getattr(event, "status", None),
            })

        return timeline

    async def get_dashboard_stats(
        self, db: AsyncSession, user_id: str
    ) -> DashboardResponse | None:
        workspaces = await self._workspace_repo.get_for_user(db, user_id, skip=0, limit=100)

        candidates = []
        for workspace in workspaces:
            sessions = await self._session_repo.get_recent_by_workspace(db, workspace.id, limit=5)
            candidates.extend(s for s in sessions if s.workflow_id)

        if not candidates:
            return None

        latest = max(candidates, key=lambda s: s.created_at)
        return await self.get_full_dashboard(db, latest.workflow_id, user_id)

    async def get_dashboard_activity(
        self, db: AsyncSession, user_id: str, limit: int = 20
    ) -> list[dict]:
        return []

    async def get_papers_for_dashboard(
        self, db: AsyncSession, workspace_id: str, user_id: str, limit: int = 10
    ) -> list[dict]:
        await self._verify_workspace_access(db, workspace_id, user_id)
        papers = await self._paper_repo.get_by_workspace(db, workspace_id, limit=limit)
        return [
            {
                "id": p.id,
                "title": p.title,
                "authors": p.authors,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in papers
        ]

    async def get_citations_for_dashboard(
        self, db: AsyncSession, workspace_id: str, user_id: str, limit: int = 10
    ) -> list[dict]:
        await self._verify_workspace_access(db, workspace_id, user_id)
        citations = await self._citation_repo.get_by_workspace(db, workspace_id, limit=limit)
        return [
            {
                "id": c.id,
                "title": c.title,
                "style": c.style,
                "formatted_citation": c.formatted_citation,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in citations
        ]

    async def get_ai_stats_for_dashboard(self, db: AsyncSession, user_id: str) -> dict:
        conversations_count = await self._conversation_repo.get_conversation_count(db, user_id)
        recent = await self._conversation_repo.list_conversations(db, user_id, limit=1)

        last_message = None
        if recent and recent[0].messages:
            last_msg = recent[0].messages[-1]
            last_message = {
                "content": last_msg.content,
                "role": last_msg.role,
                "timestamp": last_msg.timestamp.isoformat() if last_msg.timestamp else None,
            }

        all_conversations = await self._conversation_repo.list_conversations(
            db, user_id, limit=1000
        )
        model_usage: dict[str, int] = {}
        for conv in all_conversations:
            model_usage[conv.model] = model_usage.get(conv.model, 0) + 1

        return {
            "conversations_count": conversations_count,
            "last_message": last_message,
            "model_usage": model_usage,
        }
