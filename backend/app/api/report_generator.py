from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.models.user import User
from app.schemas.report_generator import (
    ResearchReport,
    ReportGenerateRequest,
    ReportExportRequest,
    ExportFormat,
)
from app.agents.report_builder import build_report_from_state, build_markdown, build_json
from app.agents.report_validation import validate_report_data, validate_export_request
from app.core.logging import get_logger
from app.services.auth_service import get_current_user

logger = get_logger("api.report_generator")
router = APIRouter(tags=["Report Generator"])


class PreviewResponse(BaseModel):
    markdown: str
    report_json: str
    metrics: dict[str, Any]
    valid: bool
    validation_errors: list[str]
    validation_warnings: list[str]


class ExportResponse(BaseModel):
    content: str
    format: str
    filename: str
    content_type: str


@router.post("/reports/generate", response_model=ResearchReport)
async def generate_report(
    body: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
) -> ResearchReport:
    """Generate a publication-quality research report from provided data."""
    report = build_report_from_state(
        query=body.query,
        planner_raw=body.planner_output,
        summaries=body.summaries,
        gaps=body.research_gaps,
        objective=body.objective,
    )

    validation = validate_report_data(
        body.query,
        [s.model_dump() for s in report.sections],
        [r.model_dump() for r in report.references],
        report.conclusion,
    )

    if validation.errors:
        logger.warning("report generated with validation errors", extra={"errors": validation.errors})

    return report


@router.post("/reports/preview", response_model=PreviewResponse)
async def preview_report(
    body: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
) -> PreviewResponse:
    """Generate a report and return structured preview."""
    report = build_report_from_state(
        query=body.query,
        planner_raw=body.planner_output,
        summaries=body.summaries,
        gaps=body.research_gaps,
        objective=body.objective,
    )

    validation = validate_report_data(
        body.query,
        [s.model_dump() for s in report.sections],
        [r.model_dump() for r in report.references],
        report.conclusion,
    )

    return PreviewResponse(
        markdown=report.markdown,
        json=report.report_json,
        metrics=report.metrics.model_dump(),
        valid=validation.valid,
        validation_errors=validation.errors,
        validation_warnings=validation.warnings,
    )


@router.post("/reports/export", response_model=ExportResponse)
async def export_report(
    body: ReportExportRequest,
    current_user: User = Depends(get_current_user),
) -> ExportResponse:
    """Export a report in the requested format."""
    validation = validate_export_request(
        body.report.model_dump() if body.report else None,
        body.format.value if hasattr(body.format, "value") else str(body.format),
    )

    if validation.errors:
        raise HTTPException(status_code=400, detail=validation.errors)

    fmt = body.format.value if hasattr(body.format, "value") else str(body.format)
    content_type_map = {
        "markdown": "text/markdown",
        "json": "application/json",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "html": "text/html",
    }

    if fmt == "markdown":
        content = body.report.markdown or build_markdown(body.report)
    elif fmt == "json":
        content = body.report.report_json or build_json(body.report)
    elif fmt == "pdf":
        content = "# PDF export is not yet implemented.\n\n" + build_markdown(body.report)
    elif fmt == "docx":
        content = "# DOCX export is not yet implemented.\n\n" + build_markdown(body.report)
    elif fmt == "html":
        md = body.report.markdown or build_markdown(body.report)
        content = f"<html><body><pre>{md}</pre></body></html>"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}")

    filename = f"report_{body.report.query[:30].replace(' ', '_').lower()}.{fmt}"
    content_type = content_type_map.get(fmt, "text/plain")

    return ExportResponse(
        content=content,
        format=fmt,
        filename=filename,
        content_type=content_type,
    )
