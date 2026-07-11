from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.models.citation import Citation
from app.repositories import CitationRepository, PaperRepository, WorkspaceRepository
from app.schemas.citation import (
    CitationCreate,
    CitationExportRequest,
    CitationExportResponse,
    CitationLibrarySummary,
    CitationResponse,
    CitationUpdate,
)


class CitationService:
    def __init__(
        self,
        repo: CitationRepository,
        paper_repo: PaperRepository,
    ) -> None:
        self._repo = repo
        self._paper_repo = paper_repo

    async def create_citation(
        self, db: AsyncSession, workspace_id: str, user_id: str, data: CitationCreate
    ) -> CitationResponse:
        await self._verify_workspace_access(db, workspace_id, user_id)

        citation = await self._repo.create(
            db,
            workspace_id=workspace_id,
            paper_id=data.paper_id,
            raw_citation_text=data.title,
            style=data.style,
            source_type=data.source_type,
            authors=data.authors,
            title=data.title,
            year=data.year,
            journal=data.journal,
            volume=data.volume,
            issue=data.issue,
            pages=data.pages,
            doi=data.doi,
            url=data.url,
            isbn=data.isbn,
            publisher=data.publisher,
        )

        formatted = self._format_citation(citation)
        citation = await self._repo.update(db, citation.id, formatted_citation=formatted)

        return self._to_response(citation)

    async def update_citation(
        self, db: AsyncSession, citation_id: str, user_id: str, data: CitationUpdate
    ) -> CitationResponse:
        citation = await self._repo.get(db, citation_id)
        await self._verify_workspace_access(db, citation.workspace_id, user_id)

        update_kwargs = data.model_dump(exclude_unset=True)
        if update_kwargs:
            citation = await self._repo.update(db, citation_id, **update_kwargs)
            formatted = self._format_citation(citation)
            citation = await self._repo.update(db, citation_id, formatted_citation=formatted)

        return self._to_response(citation)

    async def delete_citation(
        self, db: AsyncSession, citation_id: str, user_id: str
    ) -> None:
        citation = await self._repo.get(db, citation_id)
        await self._verify_workspace_access(db, citation.workspace_id, user_id)
        await self._repo.delete(db, citation_id)

    async def get_citation(
        self, db: AsyncSession, citation_id: str, user_id: str
    ) -> CitationResponse:
        citation = await self._repo.get(db, citation_id)
        await self._verify_workspace_access(db, citation.workspace_id, user_id)
        return self._to_response(citation)

    async def list_citations(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        skip: int,
        limit: int,
    ) -> tuple[list[CitationResponse], int]:
        await self._verify_workspace_access(db, workspace_id, user_id)

        citations = await self._repo.get_by_workspace(db, workspace_id, skip=skip, limit=limit)
        total = len(await self._repo.get_by_workspace(db, workspace_id))

        return [self._to_response(c) for c in citations], total

    async def export_citations(
        self, db: AsyncSession, user_id: str, data: CitationExportRequest
    ) -> CitationExportResponse:
        citations = []
        for cid in data.citation_ids:
            try:
                citation = await self._repo.get(db, cid)
                await self._verify_workspace_access(db, citation.workspace_id, user_id)
                citations.append(citation)
            except Exception:
                continue

        formatted = []
        for c in citations:
            cit_data = {
                "authors": c.authors or [],
                "title": c.title or "",
                "year": c.year,
                "journal": c.journal or "",
                "volume": c.volume or "",
                "issue": c.issue or "",
                "pages": c.pages or "",
                "doi": c.doi or "",
                "url": c.url or "",
                "publisher": c.publisher or "",
                "isbn": c.isbn or "",
            }
            formatted.append(self.generate_citation_text(cit_data, data.format))

        content = "\n\n".join(formatted)
        ext_map = {"bibtex": "bib", "ris": "ris", "apa": "txt", "mla": "txt", "ieee": "txt"}
        filename = f"citations.{ext_map.get(data.format, 'txt')}"

        return CitationExportResponse(format=data.format, content=content, filename=filename)

    async def get_library_summary(
        self, db: AsyncSession, workspace_id: str, user_id: str
    ) -> CitationLibrarySummary:
        await self._verify_workspace_access(db, workspace_id, user_id)

        total = len(await self._repo.get_by_workspace(db, workspace_id))
        by_style = await self._repo.count_by_style(db, workspace_id)
        by_source_type = await self._repo.count_by_source_type(db, workspace_id)

        return CitationLibrarySummary(
            total_citations=total,
            by_style=by_style,
            by_source_type=by_source_type,
        )

    def generate_citation_text(self, citation: dict[str, Any], style: str) -> str:
        authors = citation.get("authors", [])
        title = citation.get("title", "")
        year = citation.get("year")
        journal = citation.get("journal", "")
        volume = citation.get("volume", "")
        issue = citation.get("issue", "")
        pages = citation.get("pages", "")
        doi = citation.get("doi", "")
        url = citation.get("url", "")
        citation.get("publisher", "")
        citation.get("isbn", "")

        if style == "bibtex":
            key = authors[0].split(",")[0].strip().lower() if authors else "unknown"
            key = f"{key}{year}" if year else key
            parts = [f"@article{{{key},"]
            if authors:
                parts.append(f"  author = {{{' and '.join(authors)}}},")
            if title:
                parts.append(f"  title = {{{title}}},")
            if journal:
                parts.append(f"  journal = {{{journal}}},")
            if year:
                parts.append(f"  year = {{{year}}},")
            if volume:
                parts.append(f"  volume = {{{volume}}},")
            if issue:
                parts.append(f"  number = {{{issue}}},")
            if pages:
                parts.append(f"  pages = {{{pages}}},")
            if doi:
                parts.append(f"  doi = {{{doi}}},")
            parts.append("}")
            return "\n".join(parts)

        elif style == "ris":
            lines = ["TY  - JOUR"]
            for a in authors:
                lines.append(f"AU  - {a}")
            lines.append(f"TI  - {title}")
            if year:
                lines.append(f"PY  - {year}")
            if journal:
                lines.append(f"JO  - {journal}")
            if volume:
                lines.append(f"VL  - {volume}")
            if issue:
                lines.append(f"IS  - {issue}")
            if pages and "-" in pages:
                sp, ep = pages.split("-", 1)
                lines.append(f"SP  - {sp.strip()}")
                lines.append(f"EP  - {ep.strip()}")
            elif pages:
                lines.append(f"SP  - {pages}")
            if doi:
                lines.append(f"DO  - {doi}")
            lines.append("ER  - ")
            return "\n".join(lines)

        elif style == "apa":
            author_str = self._format_authors_apa(authors)
            year_str = f"({year})" if year else "(n.d.)"
            title_str = f"*{title}*" if journal else title
            source = ""
            if journal:
                vol_issue = f"*{volume}*" if volume else ""
                if issue:
                    vol_issue += f"({issue})"
                source_parts = [f"*{journal}*, {vol_issue}" if vol_issue else f"*{journal}*"]
                if pages:
                    source_parts.append(pages)
                source = ", ".join(source_parts)
            doi_str = f"https://doi.org/{doi}" if doi else url or ""
            parts = [p for p in [f"{author_str} {year_str}.", title_str, source, doi_str] if p]
            return " ".join(parts)

        elif style == "mla":
            author_str = self._format_authors_mla(authors)
            title_str = f"\"{title}.\"" if title else ""
            journal_str = f"*{journal}*," if journal else ""
            vol_str = f"vol. {volume}," if volume else ""
            issue_str = f"no. {issue}," if issue else ""
            year_str = f"{year}," if year else ""
            pages_str = f"pp. {pages}." if pages else "."
            parts = [p for p in [author_str, title_str, journal_str, vol_str, issue_str, year_str, pages_str] if p]
            return " ".join(parts)

        elif style == "ieee":
            author_str = self._format_authors_ieee(authors)
            title_str = f"\"{title},\"" if title else ""
            journal_str = f"*{journal}*," if journal else ""
            vol_str = f"vol. {volume}," if volume else ""
            issue_str = f"no. {issue}," if issue else ""
            pages_str = f"pp. {pages}," if pages else ""
            year_str = f"{year}." if year else ""
            parts = [p for p in [author_str, title_str, journal_str, vol_str, issue_str, pages_str, year_str] if p]
            return " ".join(parts)

        return title

    def _format_citation(self, citation: Citation) -> str:
        cit_data = {
            "authors": citation.authors or [],
            "title": citation.title or "",
            "year": citation.year,
            "journal": citation.journal or "",
            "volume": citation.volume or "",
            "issue": citation.issue or "",
            "pages": citation.pages or "",
            "doi": citation.doi or "",
            "url": citation.url or "",
            "publisher": citation.publisher or "",
            "isbn": citation.isbn or "",
        }
        return self.generate_citation_text(cit_data, citation.style)

    def _format_authors_apa(self, authors: list[str]) -> str:
        if not authors:
            return ""
        if len(authors) == 1:
            return authors[0]
        if len(authors) == 2:
            return f"{authors[0]} & {authors[1]}"
        return f"{authors[0]} et al."

    def _format_authors_mla(self, authors: list[str]) -> str:
        if not authors:
            return ""
        if len(authors) == 1:
            return f"{authors[0]}."
        if len(authors) == 2:
            return f"{authors[0]} and {authors[1]}."
        return f"{authors[0]}, et al."

    def _format_authors_ieee(self, authors: list[str]) -> str:
        if not authors:
            return ""
        parts = []
        for a in authors:
            name_parts = a.split(", ")
            if len(name_parts) == 2:
                parts.append(f"{name_parts[1][0]}. {name_parts[0]}")
            else:
                parts.append(a)
        return ", ".join(parts) + "," if parts else ""

    async def _verify_workspace_access(
        self, db: AsyncSession, workspace_id: str, user_id: str
    ) -> None:
        ws_repo = WorkspaceRepository()
        workspace = await ws_repo.get(db, workspace_id)
        if workspace.owner_id == user_id:
            return
        role = await ws_repo.get_member_role(db, workspace_id, user_id)
        if role is None:
            raise AuthorizationError("User does not have access to this workspace")

    def _to_response(self, citation: Citation) -> CitationResponse:
        return CitationResponse(
            id=citation.id,
            workspace_id=citation.workspace_id,
            paper_id=citation.paper_id,
            raw_citation_text=citation.raw_citation_text,
            formatted_citation=citation.formatted_citation,
            style=citation.style,
            source_type=citation.source_type,
            authors=citation.authors,
            title=citation.title,
            year=citation.year,
            journal=citation.journal,
            volume=citation.volume,
            issue=citation.issue,
            pages=citation.pages,
            doi=citation.doi,
            url=citation.url,
            isbn=citation.isbn,
            publisher=citation.publisher,
            accessed_date=citation.accessed_date,
            created_at=citation.created_at,
            updated_at=citation.updated_at,
        )
