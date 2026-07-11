from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import AgentContext
from app.agents.writing import WritingAgent
from app.repositories import DocumentRepository, WorkspaceRepository
from app.schemas.document import (
    DocumentExportResponse,
    DocumentGenerateRequest,
    DocumentResponse,
)

STORAGE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage", "documents"
)


class DocumentService:
    def __init__(
        self,
        repo: DocumentRepository,
        writing_agent: WritingAgent,
    ) -> None:
        self._repo = repo
        self._writing_agent = writing_agent

    async def generate_document(
        self, db: AsyncSession, user_id: str, data: DocumentGenerateRequest
    ) -> DocumentResponse:
        ws_repo = WorkspaceRepository()
        await ws_repo.get(db, data.workspace_id)

        context = AgentContext(
            workflow_id=f"doc_{uuid4().hex[:12]}",
            step_id="document",
            trace_id=str(uuid4()),
            input={
                "workspace_id": data.workspace_id,
                "session_id": data.session_id,
                "project_id": data.project_id,
                "template": {"name": data.template or "default"},
            },
        )

        agent_output = await self._writing_agent.execute(context)

        sections = agent_output.output.get("sections", [])
        markdown_content = self._sections_to_markdown(sections, data.title)
        formatted_content = self._format_content(markdown_content, data.format, data.title)

        os.makedirs(STORAGE_DIR, exist_ok=True)
        ext = self._format_extension(data.format)
        file_path = os.path.join(STORAGE_DIR, f"{uuid4().hex}{ext}")
        from app.services.path_validator import resolve_safe_path
        resolve_safe_path(STORAGE_DIR, file_path)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(formatted_content)

        document = await self._repo.create(
            db,
            workspace_id=data.workspace_id,
            session_id=data.session_id,
            format=data.format,
            title=data.title,
            content=formatted_content,
            file_path=file_path,
            file_size=len(formatted_content.encode("utf-8")),
            status="completed",
            template_used=data.template,
            citation_count=len(agent_output.output.get("citations", [])),
        )

        return DocumentResponse(
            id=document.id,
            workspace_id=document.workspace_id,
            session_id=document.session_id,
            format=document.format,
            title=document.title,
            content=document.content,
            file_path=document.file_path,
            file_size=document.file_size,
            status=document.status,
            version=document.version,
            citation_count=document.citation_count,
            template_used=document.template_used,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    async def get_document(
        self, db: AsyncSession, document_id: str, user_id: str
    ) -> DocumentResponse:
        document = await self._repo.get(db, document_id)
        return self._to_response(document)

    async def list_documents(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        skip: int,
        limit: int,
    ) -> tuple[list[DocumentResponse], int]:
        documents = await self._repo.get_by_workspace(db, workspace_id, skip=skip, limit=limit)
        total = len(await self._repo.get_by_workspace(db, workspace_id))
        return [self._to_response(d) for d in documents], total

    async def export_document(
        self,
        db: AsyncSession,
        document_id: str,
        user_id: str,
        fmt: str,
    ) -> DocumentExportResponse:
        document = await self._repo.get(db, document_id)
        formatted = self._format_content(document.content, fmt, document.title)

        ext = self._format_extension(fmt)
        filename = f"{document.title.replace(' ', '_')}{ext}"

        return DocumentExportResponse(
            format=fmt,
            content=formatted,
            filename=filename,
        )

    def _sections_to_markdown(
        self, sections: list[dict[str, Any]], title: str
    ) -> str:
        lines = [f"# {title}", ""]
        for section in sections:
            heading = section.get("heading", "")
            content = section.get("content", "")
            lines.append(f"## {heading}")
            lines.append("")
            lines.append(content)
            lines.append("")
        return "\n".join(lines)

    def _format_content(self, markdown: str, fmt: str, title: str) -> str:
        if fmt == "markdown":
            return markdown
        elif fmt == "html":
            return self._markdown_to_html(markdown, title)
        elif fmt == "docx":
            return markdown
        elif fmt == "pdf":
            html = self._markdown_to_html(markdown, title)
            return html
        return markdown

    def _markdown_to_html(self, markdown: str, title: str) -> str:
        html_content = []
        for line in markdown.split("\n"):
            if line.startswith("# "):
                html_content.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                html_content.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("### "):
                html_content.append(f"<h3>{line[4:]}</h3>")
            elif line.strip() == "":
                html_content.append("<br>")
            else:
                html_content.append(f"<p>{line}</p>")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ font-family: 'Times New Roman', serif; max-width: 800px; margin: 0 auto; padding: 2em; line-height: 1.6; }}
  h1 {{ text-align: center; font-size: 1.8em; margin-bottom: 1em; }}
  h2 {{ font-size: 1.4em; margin-top: 1.5em; }}
  p {{ text-align: justify; }}
</style>
</head>
<body>
{"".join(html_content)}
</body>
</html>"""
        return html

    def _format_extension(self, fmt: str) -> str:
        from app.core.exceptions import AARAError, ErrorCode
        ext_map = {"markdown": ".md", "html": ".html", "pdf": ".pdf", "docx": ".docx"}
        ext = ext_map.get(fmt)
        if ext is None:
            raise AARAError(
                ErrorCode(
                    code="INVALID_DOCUMENT_FORMAT",
                    http_status=400,
                    message=f"Unsupported document format: {fmt}. Supported: {', '.join(ext_map)}",
                )
            )
        return ext

    def _to_response(self, document: Any) -> DocumentResponse:
        return DocumentResponse(
            id=document.id,
            workspace_id=document.workspace_id,
            session_id=document.session_id,
            format=document.format,
            title=document.title,
            content=document.content,
            file_path=document.file_path,
            file_size=document.file_size,
            status=document.status,
            version=document.version,
            citation_count=document.citation_count,
            template_used=document.template_used,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
