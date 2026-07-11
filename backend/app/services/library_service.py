from __future__ import annotations

import hashlib
import os
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.models.research_paper import ResearchPaper
from app.repositories import PaperRepository, WorkspaceRepository
from app.schemas.library import (
    DuplicateCheckResponse,
    PaperResponse,
    PaperUpdate,
    PaperUploadResponse,
    PaperVersionResponse,
)
from app.services.file_validator import validate_upload_file
from app.services.path_validator import resolve_safe_path, sanitize_filename

STORAGE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage", "papers"
)


class LibraryService:
    def __init__(self, repo: PaperRepository) -> None:
        self._repo = repo

    async def upload_paper(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        file: Any,
        metadata: PaperUpdate | None = None,
    ) -> PaperUploadResponse:
        validate_upload_file(file)
        await self._verify_workspace_access(db, workspace_id, user_id)

        content = await file.read() if hasattr(file, "read") else file
        content_bytes = content if isinstance(content, bytes) else content.encode()
        content_hash = hashlib.sha256(content_bytes).hexdigest()

        os.makedirs(STORAGE_DIR, exist_ok=True)
        raw_name = sanitize_filename(getattr(file, "filename", "unknown.pdf"))
        file_ext = raw_name.split(".")[-1] if "." in raw_name else "pdf"
        file_path = os.path.join(STORAGE_DIR, f"{uuid4().hex}.{file_ext}")
        resolve_safe_path(STORAGE_DIR, file_path)

        with open(file_path, "wb") as f:
            f.write(content_bytes)

        title = (
            metadata.title
            if metadata and metadata.title
            else getattr(file, "filename", "Untitled")
        )

        paper = await self._repo.create(
            db,
            workspace_id=workspace_id,
            title=title,
            source="upload",
            file_path=file_path,
            file_type=file_ext,
            file_size=len(content_bytes),
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

    async def delete_paper(
        self, db: AsyncSession, paper_id: str, user_id: str
    ) -> None:
        paper = await self._repo.get(db, paper_id)
        await self._verify_workspace_access(db, paper.workspace_id, user_id)
        if paper.file_path and os.path.exists(paper.file_path):
            resolve_safe_path(STORAGE_DIR, paper.file_path)
            os.remove(paper.file_path)
        await self._repo.delete(db, paper_id)

    async def replace_paper(
        self, db: AsyncSession, paper_id: str, user_id: str, file: Any
    ) -> PaperUploadResponse:
        validate_upload_file(file)
        paper = await self._repo.get(db, paper_id)
        await self._verify_workspace_access(db, paper.workspace_id, user_id)

        content = await file.read() if hasattr(file, "read") else file
        content_bytes = content if isinstance(content, bytes) else content.encode()
        content_hash = hashlib.sha256(content_bytes).hexdigest()

        os.makedirs(STORAGE_DIR, exist_ok=True)
        raw_name = sanitize_filename(getattr(file, "filename", "unknown.pdf"))
        file_ext = raw_name.split(".")[-1] if "." in raw_name else "pdf"
        file_path = os.path.join(STORAGE_DIR, f"{uuid4().hex}.{file_ext}")
        resolve_safe_path(STORAGE_DIR, file_path)

        with open(file_path, "wb") as f:
            f.write(content_bytes)

        new_version = paper.version + 1
        paper = await self._repo.update(
            db,
            paper_id,
            file_path=file_path,
            file_type=file_ext,
            file_size=len(content_bytes),
            content_hash=content_hash,
            version=new_version,
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

    async def update_metadata(
        self, db: AsyncSession, paper_id: str, user_id: str, data: PaperUpdate
    ) -> PaperResponse:
        paper = await self._repo.get(db, paper_id)
        await self._verify_workspace_access(db, paper.workspace_id, user_id)
        update_kwargs = data.model_dump(exclude_unset=True)
        if update_kwargs:
            paper = await self._repo.update(db, paper_id, **update_kwargs)
        return self._to_response(paper)

    async def get_paper(
        self, db: AsyncSession, paper_id: str, user_id: str
    ) -> PaperResponse:
        paper = await self._repo.get(db, paper_id)
        await self._verify_workspace_access(db, paper.workspace_id, user_id)
        return self._to_response(paper)

    async def list_papers(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        skip: int,
        limit: int,
        status: str | None = None,
    ) -> tuple[list[PaperResponse], int]:
        await self._verify_workspace_access(db, workspace_id, user_id)
        papers = await self._repo.get_by_workspace(
            db, workspace_id, skip=skip, limit=limit, status=status
        )
        count_filters: dict[str, Any] = {"workspace_id": workspace_id}
        if status is not None:
            count_filters["status"] = status
        total = await self._repo.count(db, **count_filters)
        return [self._to_response(p) for p in papers], total

    async def check_duplicate(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        content_hash: str | None = None,
        doi: str | None = None,
    ) -> DuplicateCheckResponse:
        await self._verify_workspace_access(db, workspace_id, user_id)
        existing = None
        confidence = 0.0

        if content_hash:
            existing = await self._repo.find_by_content_hash(db, content_hash, workspace_id)
            if existing:
                confidence = 1.0

        if not existing and doi:
            existing = await self._repo.find_by_doi(db, doi, workspace_id)
            if existing:
                confidence = 0.9

        return DuplicateCheckResponse(
            is_duplicate=existing is not None,
            existing_paper=self._to_response(existing) if existing else None,
            confidence=confidence,
        )

    async def get_versions(
        self, db: AsyncSession, paper_id: str, user_id: str
    ) -> list[PaperVersionResponse]:
        paper = await self._repo.get(db, paper_id)
        await self._verify_workspace_access(db, paper.workspace_id, user_id)
        versions = []
        for v in range(1, paper.version + 1):
            versions.append(
                PaperVersionResponse(
                    version=v,
                    file_type=paper.file_type,
                    file_size=paper.file_size if v == paper.version else None,
                    created_at=paper.created_at if v == 1 else paper.updated_at,
                )
            )
        return versions

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

    def _to_response(self, paper: ResearchPaper) -> PaperResponse:
        return PaperResponse(
            id=paper.id,
            workspace_id=paper.workspace_id,
            project_id=paper.project_id,
            title=paper.title,
            authors=paper.authors,
            abstract=paper.abstract,
            source=paper.source,
            file_path=paper.file_path,
            file_type=paper.file_type,
            file_size=paper.file_size,
            doi=paper.doi,
            arxiv_id=paper.arxiv_id,
            url=paper.url,
            publication_year=paper.publication_year,
            venue=paper.venue,
            citation_count=paper.citation_count,
            status=paper.status,
            version=paper.version,
            created_at=paper.created_at,
            updated_at=paper.updated_at,
        )
