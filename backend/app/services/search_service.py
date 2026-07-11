from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import CitationRepository, PaperRepository, ProjectRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.search import SearchRequest, SearchResponse, SearchResult


class SearchService:
    def __init__(
        self,
        paper_repo: PaperRepository,
        citation_repo: CitationRepository,
        project_repo: ProjectRepository,
        vector_search: Any = None,
    ) -> None:
        self._paper_repo = paper_repo
        self._citation_repo = citation_repo
        self._project_repo = project_repo
        self._vector_search = vector_search

    async def search(
        self, db: AsyncSession, user_id: str, data: SearchRequest
    ) -> SearchResponse:
        if data.scope == "papers":
            results, total = await self._search_papers(db, data)
        elif data.scope == "citations":
            results, total = await self._search_citations(db, data)
        elif data.scope == "projects":
            results, total = await self._search_projects(db, data)
        elif data.scope == "workspace":
            results, total = await self._search_workspaces(db, data)
        elif data.scope == "semantic":
            results, total = await self._search_semantic(db, data)
        else:
            results, total = [], 0

        total_pages = max(1, (total + data.page_size - 1) // data.page_size)

        return SearchResponse(
            results=results,
            total=total,
            page=data.page,
            page_size=data.page_size,
            total_pages=total_pages,
        )

    async def _search_papers(
        self, db: AsyncSession, data: SearchRequest
    ) -> tuple[list[SearchResult], int]:
        if not data.workspace_id:
            return [], 0

        papers = await self._paper_repo.search(
            db, data.query, data.workspace_id,
            skip=(data.page - 1) * data.page_size,
            limit=data.page_size,
        )

        results = [
            SearchResult(
                id=p.id,
                type="paper",
                title=p.title,
                snippet=(p.abstract or "")[:200],
                score=1.0,
                metadata={"doi": p.doi, "authors": p.authors, "year": p.publication_year},
            )
            for p in papers
        ]

        return results, len(results)

    async def _search_citations(
        self, db: AsyncSession, data: SearchRequest
    ) -> tuple[list[SearchResult], int]:
        if not data.workspace_id:
            return [], 0

        citations = await self._citation_repo.search(
            db, data.query, data.workspace_id,
            skip=(data.page - 1) * data.page_size,
            limit=data.page_size,
        )

        results = [
            SearchResult(
                id=c.id,
                type="citation",
                title=c.title or "",
                snippet=(c.formatted_citation or "")[:200],
                score=1.0,
                metadata={"style": c.style, "source_type": c.source_type},
            )
            for c in citations
        ]

        return results, len(results)

    async def _search_projects(
        self, db: AsyncSession, data: SearchRequest
    ) -> tuple[list[SearchResult], int]:
        if not data.workspace_id:
            return [], 0

        projects = await self._project_repo.get_by_workspace(
            db, data.workspace_id,
            skip=(data.page - 1) * data.page_size,
            limit=data.page_size,
        )

        query_lower = data.query.lower()
        matched = []
        for p in projects:
            if query_lower in p.name.lower() or (
                p.description and query_lower in p.description.lower()
            ):
                matched.append(p)

        results = [
            SearchResult(
                id=p.id,
                type="project",
                title=p.name,
                snippet=(p.description or "")[:200],
                score=1.0,
                metadata={"status": p.status, "research_goal": p.research_goal},
            )
            for p in matched
        ]

        return results, len(results)

    async def _search_workspaces(
        self, db: AsyncSession, data: SearchRequest
    ) -> tuple[list[SearchResult], int]:
        ws_repo = WorkspaceRepository()
        workspaces = await ws_repo.get_for_user(db, data.workspace_id)

        query_lower = data.query.lower()
        matched = []
        for ws in workspaces:
            if query_lower in ws.name.lower() or (
                ws.description and query_lower in ws.description.lower()
            ):
                matched.append(ws)

        # paginate matched
        start = (data.page - 1) * data.page_size
        end = start + data.page_size
        page = matched[start:end]

        results = [
            SearchResult(
                id=ws.id,
                type="workspace",
                title=ws.name,
                snippet=(ws.description or "")[:200],
                score=1.0,
                metadata={"research_topic": ws.research_topic, "status": ws.status},
            )
            for ws in page
        ]

        return results, len(matched)

    async def _search_semantic(
        self, db: AsyncSession, data: SearchRequest
    ) -> tuple[list[SearchResult], int]:
        if not self._vector_search:
            return [], 0

        if not data.workspace_id:
            return [], 0

        try:
            if hasattr(self._vector_search, "search"):
                vector_results = await self._vector_search.search(
                    collection_name=f"workspace_{data.workspace_id}",
                    query_text=data.query,
                    limit=data.page_size,
                    offset=(data.page - 1) * data.page_size,
                    filters=data.filters,
                )

                results = [
                    SearchResult(
                        id=r.get("id", ""),
                        type="paper",
                        title=r.get("title", ""),
                        snippet=r.get("snippet", "")[:200],
                        score=r.get("score", 0.0),
                        metadata=r.get("metadata", {}),
                    )
                    for r in vector_results
                ]

                return results, len(results)
        except Exception:
            pass

        return [], 0
