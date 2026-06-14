from __future__ import annotations

from typing import Any


class ValidationResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0

    def merge(self, other: ValidationResult) -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


def validate_report_data(
    query: str,
    sections: list[dict[str, Any]],
    references: list[dict[str, Any]],
    conclusion: str,
) -> ValidationResult:
    """Validate report completeness before generation."""
    result = ValidationResult()

    if not query or not query.strip():
        result.errors.append("Report query/title is empty")

    if not sections:
        result.errors.append("No sections generated for the report")
    else:
        for i, s in enumerate(sections):
            title = s.get("title") or s.get("subtopic", "")
            if not title.strip():
                result.errors.append(f"Section {i+1} is missing a title")
            if not s.get("summary", "").strip():
                result.warnings.append(f"Section '{title}' has no summary text")

    if not references:
        result.errors.append("No references collected for the report")

    if not conclusion or not conclusion.strip():
        result.errors.append("Report conclusion is missing")

    # Check for minimum viable report
    if len(sections) < 1:
        result.errors.append("Report must contain at least one section")

    return result


def validate_export_request(
    report: dict[str, Any] | None,
    fmt: str,
) -> ValidationResult:
    """Validate an export request."""
    result = ValidationResult()

    if not report:
        result.errors.append("No report data provided for export")
        return result

    if fmt not in ("markdown", "json", "pdf", "docx", "html"):
        result.errors.append(f"Unsupported export format: {fmt}")

    if not report.get("markdown") and not report.get("sections"):
        result.warnings.append("Report has no content to export")

    return result
