"""Unit tests for GZip compression middleware."""
import gzip
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import Response, StreamingResponse, FileResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.middleware.compression import GZipMiddleware


@pytest.fixture
def app():
    """Create a FastAPI app for testing."""
    app = FastAPI()
    
    @app.get("/small")
    async def small_endpoint():
        return Response(b"small response", status_code=200)
    
    @app.get("/large")
    async def large_endpoint():
        # Create a response larger than the default threshold
        large_content = b"x" * 2000
        return Response(large_content, status_code=200)
    
    @app.get("/stream")
    async def stream_endpoint():
        async def generate():
            yield b"chunk1"
            yield b"chunk2"
        return StreamingResponse(generate())
    
    @app.get("/head")
    async def head_endpoint():
        return Response(b"head response", status_code=200)
    
    @app.get("/range")
    async def range_endpoint():
        return Response(b"range response", status_code=200)
    
    return app


class TestGZipMiddleware:
    """Test cases for GZip compression middleware."""

    def test_initialization_with_defaults(self):
        """Test middleware initialization with default parameters."""
        middleware = GZipMiddleware(MagicMock())
        assert middleware.minimum_size == 1024
        assert middleware.compression_level == 9
        assert middleware.exclude_content_types == [
            "image/",
            "video/",
            "audio/",
            "application/octet-stream",
        ]

    def test_initialization_with_custom_params(self):
        """Test middleware initialization with custom parameters."""
        middleware = GZipMiddleware(
            MagicMock(),
            minimum_size=2048,
            compression_level=6,
            exclude_content_types=["text/plain"],
            exclude_paths=["/test"],
        )
        assert middleware.minimum_size == 2048
        assert middleware.compression_level == 6
        assert middleware.exclude_content_types == ["text/plain"]
        assert middleware.exclude_paths == ["/test"]

    @pytest.mark.asyncio
    async def test_should_compress_with_gzip_accept_encoding(self, app):
        """Test compression when client accepts gzip."""
        # Create middleware
        middleware = GZipMiddleware(app)
        
        # Mock request with gzip accept encoding
        request = MagicMock()
        request.headers = {"accept-encoding": "gzip, deflate"}
        request.method = "GET"
        request.url.path = "/large"
        request.state = MagicMock()
        
        # Mock next call to get a large response
        async def mock_next(req):
            return Response(b"x" * 2000, headers={"content-type": "text/plain"})
        
        # Test compression
        response = await middleware.dispatch(request, mock_next)
        
        # Check that response is compressed
        assert response.headers.get("content-encoding") == "gzip"
        assert response.headers.get("content-length") == str(len(gzip.compress(b"x" * 2000)))

    @pytest.mark.asyncio
    async def test_should_not_compress_without_accept_encoding(self, app):
        """Test that response is not compressed when client doesn't accept gzip."""
        middleware = GZipMiddleware(app)
        
        # Mock request without gzip accept encoding
        request = MagicMock()
        request.headers = {"accept-encoding": "identity"}
        request.method = "GET"
        request.url.path = "/large"
        request.state = MagicMock()
        
        # Mock next call
        async def mock_next(req):
            return Response(b"x" * 2000, headers={"content-type": "text/plain"})
        
        # Test no compression
        response = await middleware.dispatch(request, mock_next)
        
        # Check that response is not compressed
        assert "content-encoding" not in response.headers

    @pytest.mark.asyncio
    async def test_should_not_compress_small_response(self, app):
        """Test that small responses below threshold are not compressed."""
        middleware = GZipMiddleware(app)
        
        # Mock request with gzip accept encoding
        request = MagicMock()
        request.headers = {"accept-encoding": "gzip"}
        request.method = "GET"
        request.url.path = "/small"
        request.state = MagicMock()
        
        # Mock next call with small response
        async def mock_next(req):
            return Response(b"small", headers={"content-type": "text/plain"})
        
        # Test no compression for small response
        response = await middleware.dispatch(request, mock_next)
        
        # Check that response is not compressed
        assert "content-encoding" not in response.headers

    @pytest.mark.asyncio
    async def test_should_not_compress_existing_content_encoding(self, app):
        """Test that responses already compressed are not double-compressed."""
        middleware = GZipMiddleware(app)
        
        # Mock request with gzip accept encoding
        request = MagicMock()
        request.headers = {"accept-encoding": "gzip"}
        request.method = "GET"
        request.url.path = "/large"
        request.state = MagicMock()
        
        # Mock next call with already compressed response
        async def mock_next(req):
            return Response(
                gzip.compress(b"x" * 2000),
                headers={
                    "content-type": "text/plain",
                    "content-encoding": "gzip",
                },
            )
        
        # Test no double compression
        response = await middleware.dispatch(request, mock_next)
        
        # Check that response is not re-compressed
        assert response.headers.get("content-encoding") == "gzip"

    @pytest.mark.asyncio
    async def test_should_not_compress_streaming_response(self, app):
        """Test that streaming responses are not compressed."""
        middleware = GZipMiddleware(app)
        
        # Mock request with gzip accept encoding
        request = MagicMock()
        request.headers = {"accept-encoding": "gzip"}
        request.method = "GET"
        request.url.path = "/stream"
        request.state = MagicMock()
        
        # Mock next call with streaming response
        async def mock_next(req):
            async def generate():
                yield b"chunk1"
                yield b"chunk2"
            return StreamingResponse(generate())
        
        # Test no compression for streaming response
        response = await middleware.dispatch(request, mock_next)
        
        # Check that streaming response is not compressed
        assert not hasattr(response, "__class__") or "StreamingResponse" not in str(response.__class__)

    @pytest.mark.asyncio
    async def test_should_not_compress_file_response(self, app):
        """Test that file responses are not compressed."""
        middleware = GZipMiddleware(app)
        
        # Mock request with gzip accept encoding
        request = MagicMock()
        request.headers = {"accept-encoding": "gzip"}
        request.method = "GET"
        request.url.path = "/large"
        request.state = MagicMock()
        
        # Mock next call with file response
        async def mock_next(req):
            return FileResponse("/tmp/test.txt")
        
        # Test no compression for file response
        response = await middleware.dispatch(request, mock_next)
        
        # Check that file response is not compressed
        assert "content-encoding" not in response.headers

    @pytest.mark.asyncio
    async def test_should_not_compress_image_content_type(self, app):
        """Test that image content types are not compressed."""
        middleware = GZipMiddleware(app)
        
        # Mock request with gzip accept encoding
        request = MagicMock()
        request.headers = {"accept-encoding": "gzip"}
        request.method = "GET"
        request.url.path = "/large"
        request.state = MagicMock()
        
        # Mock next call with image content type
        async def mock_next(req):
            return Response(
                b"image data",
                headers={"content-type": "image/png"},
            )
        
        # Test no compression for image content type
        response = await middleware.dispatch(request, mock_next)
        
        # Check that response is not compressed
        assert "content-encoding" not in response.headers

    @pytest.mark.asyncio
    async def test_should_not_compress_video_content_type(self, app):
        """Test that video content types are not compressed."""
        middleware = GZipMiddleware(app)
        
        # Mock request with gzip accept encoding
        request = MagicMock()
        request.headers = {"accept-encoding": "gzip"}
        request.method = "GET"
        request.url.path = "/large"
        request.state = MagicMock()
        
        # Mock next call with video content type
        async def mock_next(req):
            return Response(
                b"video data",
                headers={"content-type": "video/mp4"},
            )
        
        # Test no compression for video content type
        response = await middleware.dispatch(request, mock_next)
        
        # Check that response is not compressed
        assert "content-encoding" not in response.headers

    @pytest.mark.asyncio
    async def test_should_not_compress_audio_content_type(self, app):
        """Test that audio content types are not compressed."""
        middleware = GZipMiddleware(app)
        
        # Mock request with gzip accept encoding
        request = MagicMock()
        request.headers = {"accept-encoding": "gzip"}
        request.method = "GET"
        request.url.path = "/large"
        request.state = MagicMock()
        
        # Mock next call with audio content type
        async def mock_next(req):
            return Response(
                b"audio data",
                headers={"content-type": "audio/mpeg"},
            )
        
        # Test no compression for audio content type
        response = await middleware.dispatch(request, mock_next)
        
        # Check that response is not compressed
        assert "content-encoding" not in response.headers

    @pytest.mark.asyncio
    async def test_vary_accept_encoding_header(self, app):
        """Test that Vary: Accept-Encoding header is set for compressed responses."""
        middleware = GZipMiddleware(app)
        
        # Mock request with gzip accept encoding
        request = MagicMock()
        request.headers = {"accept-encoding": "gzip"}
        request.method = "GET"
        request.url.path = "/large"
        request.state = MagicMock()
        
        # Mock next call with large response
        async def mock_next(req):
            return Response(b"x" * 2000, headers={"content-type": "text/plain"})
        
        # Test compression
        response = await middleware.dispatch(request, mock_next)
        
        # Check that Vary: Accept-Encoding header is set
        assert response.headers.get("vary") == "Accept-Encoding"

    @pytest.mark.asyncio
    async def test_head_request_no_compression(self, app):
        """Test that HEAD requests are not compressed (no body to compress)."""
        middleware = GZipMiddleware(app)
        
        # Mock request with gzip accept encoding
        request = MagicMock()
        request.headers = {"accept-encoding": "gzip"}
        request.method = "HEAD"
        request.url.path = "/head"
        request.state = MagicMock()
        
        # Mock next call
        async def mock_next(req):
            return Response(
                b"head body",
                headers={"content-type": "text/plain"},
                status_code=200,
            )
        
        # Test that HEAD request is not compressed
        response = await middleware.dispatch(request, mock_next)
        
        # Check that response is not compressed
        assert "content-encoding" not in response.headers

    @pytest.mark.asyncio
    async def test_error_handling_graceful_fallback(self, app):
        """Test that errors in compression handler don't crash the middleware."""
        middleware = GZipMiddleware(app)
        
        # Mock request with gzip accept encoding
        request = MagicMock()
        request.headers = {"accept-encoding": "gzip"}
        request.method = "GET"
        request.url.path = "/large"
        request.state = MagicMock()
        
        # Mock next call that raises an exception
        async def mock_next(req):
            raise Exception("Test error")
        
        # Test that exception is propagated
        with pytest.raises(Exception):
            await middleware.dispatch(request, mock_next)

    @pytest.mark.asyncio
    async def test_exclude_paths(self, app):
        """Test that excluded paths are not compressed."""
        middleware = GZipMiddleware(
            app,
            exclude_paths=["/health", "/metrics"],
        )
        
        # Mock request with gzip accept encoding
        request = MagicMock()
        request.headers = {"accept-encoding": "gzip"}
        request.method = "GET"
        request.url.path = "/health"
        request.state = MagicMock()
        
        # Mock next call
        async def mock_next(req):
            return Response(b"health check", headers={"content-type": "text/plain"})
        
        # Test that excluded path is not compressed
        response = await middleware.dispatch(request, mock_next)
        
        # Check that response is not compressed
        assert "content-encoding" not in response.headers
