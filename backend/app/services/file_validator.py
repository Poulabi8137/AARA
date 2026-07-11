from __future__ import annotations

import os
from typing import Any

from app.core.exceptions import AARAError, ErrorCode


def _reject_path_traversal(filename: str) -> None:
    if ".." in filename or "/" in filename or "\\" in filename or "\0" in filename:
        raise AARAError(
            ErrorCode(
                code="INVALID_FILENAME",
                http_status=400,
                message="Filename contains invalid characters",
            )
        )


def validate_upload_file(file: Any, max_size_mb: int = 50, allowed_types: list[str] | None = None) -> None:
    if allowed_types is None:
        allowed_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "text/markdown",
        ]

    content_type = getattr(file, "content_type", None) or getattr(file, "media_type", None)
    if isinstance(content_type, str) and content_type not in allowed_types:
        raise AARAError(
            ErrorCode(
                code="INVALID_FILE_TYPE",
                http_status=400,
                message=f"File type '{content_type}' not allowed. Allowed: {', '.join(allowed_types)}",
            )
        )

    file_size = getattr(file, "size", None)
    if isinstance(file_size, (int, float)) and file_size > max_size_mb * 1024 * 1024:
        raise AARAError(
            ErrorCode(
                code="FILE_TOO_LARGE",
                http_status=400,
                message=f"File exceeds maximum size of {max_size_mb}MB",
            )
        )

    filename = getattr(file, "filename", None)
    if filename:
        _reject_path_traversal(filename)
        ext = os.path.splitext(filename)[1].lower()
        allowed_exts = {".pdf", ".docx", ".txt", ".md"}
        if ext not in allowed_exts:
            raise AARAError(
                ErrorCode(
                    code="INVALID_FILE_EXTENSION",
                    http_status=400,
                    message=f"File extension '{ext}' not allowed. Allowed: {', '.join(allowed_exts)}",
                )
            )
