from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class GZipMiddleware(BaseHTTPMiddleware):
    """GZip compression middleware to reduce bandwidth usage and improve performance."""

    def __init__(self, app, minimum_size=1024):
        super().__init__(app)
        self.minimum_size = minimum_size

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Only compress if the client accepts gzip encoding
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding:
            return response

        content = response.body
        content_length = len(content)

        # Skip compression if content is smaller than minimum size
        if content_length < self.minimum_size:
            return response

        # Import gzip here to avoid unnecessary dependency
        import gzip

        # Compress the content
        compressed_content = gzip.compress(content)

        # Create a new response with compressed content
        compressed_response = Response(
            content=compressed_content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )

        # Set appropriate headers
        compressed_response.headers["content-encoding"] = "gzip"
        compressed_response.headers["content-length"] = str(len(compressed_content))
        compressed_response.headers["content-type"] = response.headers.get("content-type", "")

        return compressed_response


def setup_compression_middleware(app):
    """Setup GZip compression middleware."""
    app.add_middleware(GZipMiddleware, minimum_size=1024)
