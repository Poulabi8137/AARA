from __future__ import annotations

import gzip
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class GZipMiddleware(BaseHTTPMiddleware):
    """GZip compression middleware to reduce bandwidth usage and improve performance."""

    def __init__(
        self,
        app,
        minimum_size: int = 1024,
        compression_level: int = 9,
        exclude_content_types: Optional[list[str]] = None,
        exclude_paths: Optional[list[str]] = None,
    ):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compression_level = compression_level
        self.exclude_content_types = exclude_content_types or [
            "image/",
            "video/",
            "audio/",
            "application/octet-stream",
        ]
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/static/",
        ]

    def _should_compress(self, request: Request, response: Response) -> bool:
        """Determine if a response should be compressed."""
        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding:
            return False

        # Check if response is already compressed
        if response.headers.get("content-encoding"):
            return False

        # Check content type
        content_type = response.headers.get("content-type", "")
        if any(
            content_type.startswith(exclude) for exclude in self.exclude_content_types
        ):
            return False

        # Check path
        path = request.url.path
        if any(path.startswith(exclude) for exclude in self.exclude_paths):
            return False

        # Check if it's a streaming response (cannot compress)
        if (
            hasattr(response, "__class__")
            and "StreamingResponse" in response.__class__.__name__
        ):
            return False

        # Check if it's a file response (cannot compress safely)
        if (
            hasattr(response, "__class__")
            and "FileResponse" in response.__class__.__name__
        ):
            return False

        # Check if request method is HEAD (should not compress body)
        if request.method.upper() == "HEAD":
            return False

        # Check minimum size
        content = response.body
        if len(content) < self.minimum_size:
            return False

        return True

    def _compress_content(self, content: bytes) -> bytes:
        """Compress content using GZip."""
        return gzip.compress(content, compresslevel=self.compression_level)

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Skip compression for certain response types
        if not isinstance(response, Response):
            return response

        # Check if we should compress this response
        if not self._should_compress(request, response):
            return response

        # Get the content
        content = response.body

        # Compress the content
        compressed_content = self._compress_content(content)

        # Create a new response with compressed content
        compressed_response = Response(
            content=compressed_content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )

        # Set appropriate headers
        compressed_response.headers["content-encoding"] = "gzip"
        compressed_response.headers["content-length"] = str(len(compressed_content))
        compressed_response.headers["content-type"] = response.headers.get(
            "content-type", ""
        )
        compressed_response.headers["vary"] = "Accept-Encoding"

        return compressed_response


def setup_compression_middleware(
    app,
    minimum_size: int = 1024,
    compression_level: int = 9,
    exclude_content_types: Optional[list[str]] = None,
    exclude_paths: Optional[list[str]] = None,
):
    """Setup GZip compression middleware."""
    app.add_middleware(
        GZipMiddleware,
        minimum_size=minimum_size,
        compression_level=compression_level,
        exclude_content_types=exclude_content_types,
        exclude_paths=exclude_paths,
    )
