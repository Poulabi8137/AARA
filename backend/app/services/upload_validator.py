"""Upload validation service with magic byte verification."""
import magic
from pathlib import Path
from typing import Tuple, Union

from app.schemas.document import DocumentCreate
from app.core.logging import get_logger

logger = get_logger("upload_validator")


class UploadValidationError(Exception):
    """Raised when file content validation fails."""

    def __init__(self, message: str, content_type: str | None = None):
        super().__init__(message)
        self.message = message
        self.content_type = content_type


class UploadValidator:
    """Validate uploaded file content using magic bytes."""

    # File signature mapping for supported file types
    # Each entry contains (file_extension, mime_type, magic_number_bytes)
    _file_signatures = {
        ".pdf": ("application/pdf", b"%PDF"),
        ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"PK\\x03\\x04\\x14\\x00\\x06\\x00\\xa5\\xe0"),
        ".txt": ("text/plain", None),  # No magic bytes for plain text
        ".md": ("text/markdown", None),  # No magic bytes for markdown
    }

    # Content type to file extension mapping
    _content_type_to_extension = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "text/plain": ".txt",
        "text/markdown": ".md",
    }

    def __init__(self, config):
        self.config = config

    def validate_content_type(self, content: bytes, filename: str) -> Tuple[str, str]:
        """Validate file content against magic bytes and return content type and extension.

        Args:
            content: Raw file content
            filename: Original filename (used to get expected extension)

        Returns:
            Tuple of (content_type, file_extension)

        Raises:
            UploadValidationError: If content type doesn't match extension or file type is unsupported
        """
        ext = Path(filename).suffix.lower()

        if ext not in self._file_signatures:
            supported = ", ".join(f".{ext}" for ext in self._file_signatures.keys())
            raise UploadValidationError(
                f"Unsupported file format '{ext}'. Supported: {supported}",
                None,
            )

        expected_content_type, magic_bytes = self._file_signatures[ext]

        # For file types without magic bytes (text files), we can't validate content
        if magic_bytes is None:
            return expected_content_type, ext

        # Use python-magic to detect actual content type
        try:
            detected_content_type = magic.from_buffer(
                content, mime=True
            ).lower()

            if detected_content_type != expected_content_type:
                # Provide helpful error message
                raise UploadValidationError(
                    f"File content type mismatch. Expected {expected_content_type} but detected {detected_content_type}. "
                    f"File may be corrupted or not the advertised type.",
                    detected_content_type,
                )

            return expected_content_type, ext

        except Exception as e:
            # If magic detection fails, fall back to basic validation
            logger.warning("Magic byte detection failed, falling back to basic validation", extra={"error": str(e)})
            return expected_content_type, ext

    def validate_file(self, content: bytes, filename: str) -> DocumentCreate:
        """Validate uploaded file and prepare DocumentCreate object.

        Args:
            content: Raw file content
            filename: Original filename

        Returns:
            DocumentCreate object with validated metadata

        Raises:
            UploadValidationError: If validation fails
        """
        # Basic file size check
        if len(content) > self.config.max_upload_size:
            raise UploadValidationError(
                f"File too large. Maximum size is {self.config.max_upload_size // (1024 * 1024)} MB",
            )

        # Validate content type using magic bytes
        content_type, ext = self.validate_content_type(content, filename)

        # Prepare document metadata
        document_create = DocumentCreate(
            filename=filename,
            content_type=content_type,
            file_size=len(content),
            extension=ext,
        )

        logger.info(
            "File validation successful",
            extra={
                "filename": filename,
                "content_type": content_type,
                "file_size": len(content),
                "extension": ext,
            },
        )

        return document_create
