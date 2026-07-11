from __future__ import annotations

import os


def sanitize_filename(filename: str) -> str:
    if not filename or not isinstance(filename, str):
        return "unknown"
    if ".." in filename or "/" in filename or "\\" in filename or "\0" in filename:
        return "unknown"
    return filename


def resolve_safe_path(base_dir: str, file_path: str) -> str:
    resolved = os.path.realpath(file_path)
    base_resolved = os.path.realpath(base_dir)
    if not resolved.startswith(base_resolved):
        from app.core.exceptions import AARAError, ErrorCode
        raise AARAError(
            ErrorCode(
                code="PATH_TRAVERSAL_DETECTED",
                http_status=400,
                message="Path traversal detected",
            )
        )
    if os.path.islink(file_path):
        link_target = os.readlink(file_path)
        if not os.path.realpath(link_target).startswith(base_resolved):
            from app.core.exceptions import AARAError, ErrorCode
            raise AARAError(
                ErrorCode(
                    code="SYMLINK_TRAVERSAL_DETECTED",
                    http_status=400,
                    message="Symlink target outside allowed directory",
                )
            )
    return resolved


def validate_path_within(base_dir: str, target_path: str) -> str:
    resolved = os.path.realpath(target_path)
    base_resolved = os.path.realpath(base_dir)
    if not resolved.startswith(base_resolved):
        from app.core.exceptions import AARAError, ErrorCode
        raise AARAError(
            ErrorCode(
                code="PATH_TRAVERSAL_DETECTED",
                http_status=400,
                message="Path traversal detected",
            )
        )
    return resolved
