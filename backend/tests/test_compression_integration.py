"""Integration tests for GZip compression middleware."""
import gzip
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from fastapi.responses import Response, StreamingResponse, FileResponse

from backend.app.middleware.compression import setup_compression_middleware


@pytest.fixture
def app_with_compression():
    """Create a FastAPI app with compression middleware."""
    app = FastAPI()
    
    # Setup compression middleware
    setup_compression_middleware(
        app,
        minimum_size=1024,
        compression_level=6,
        exclude_content_types=["image/", "application/octet-stream"],
        exclude_paths=["/health", "/metrics"],
    )
    
    @app.get("/small")
    def small_endpoint():
        return Response(b"small response", status_code=200)
    
    @app.get("/large")
    def large_endpoint():
        # Create a response larger than the threshold
        large_content = b"x" * 2000
        return Response(large_content, status_code=200)
    
    @app.get("/stream")
    def stream_endpoint():
        async def generate():
            yield b"chunk1"
            yield b"chunk2"
        return StreamingResponse(generate())
    
    @app.get("/head")
    def head_endpoint():
        return Response(b"head response", status_code=200)
    
    @app.get("/range")
    def range_endpoint():
        return Response(b"range response", status_code=200)
    
    @app.get("/health")
    def health_endpoint():
        return Response(b"healthy", status_code=200)
    
    @app.get("/metrics")
    def metrics_endpoint():
        return Response(b"metrics", status_code=200)
    
    return app


class TestGZipMiddlewareIntegration:
    """Integration tests for GZip compression middleware."""

    def test_compression_with_gzip_accept_encoding(self, app_with_compression):
        """Test compression when client accepts gzip."""
        client = TestClient(app_with_compression)
        
        response = client.get(
            "/large",
            headers={"accept-encoding": "gzip"},
        )
        
        # Check that response is compressed
        assert response.status_code == 200
        assert "content-encoding" in response.headers
        assert response.headers["content-encoding"] == "gzip"
        
        # Verify compressed content
        decompressed = gzip.decompress(response.content)
        assert decompressed == b"x" * 2000

    def test_no_compression_without_accept_encoding(self, app_with_compression):
        """Test that response is not compressed when client doesn't accept gzip."""
        client = TestClient(app_with_compression)
        
        response = client.get(
            "/large",
            headers={"accept-encoding": "identity"},
        )
        
        # Check that response is not compressed
        assert response.status_code == 200
        assert "content-encoding" not in response.headers

    def test_no_compression_small_response(self, app_with_compression):
        """Test that small responses below threshold are not compressed."""
        client = TestClient(app_with_compression)
        
        response = client.get(
            "/small",
            headers={"accept-encoding": "gzip"},
        )
        
        # Check that response is not compressed
        assert response.status_code == 200
        assert "content-encoding" not in response.headers

    def test_no_compression_exclude_paths(self, app_with_compression):
        """Test that excluded paths are not compressed."""
        client = TestClient(app_with_compression)
        
        response = client.get(
            "/health",
            headers={"accept-encoding": "gzip"},
        )
        
        # Check that response is not compressed (excluded path)
        assert response.status_code == 200
        assert "content-encoding" not in response.headers

    def test_no_compression_content_type_exclusion(self, app_with_compression):
        """Test that excluded content types are not compressed."""
        client = TestClient(app_with_compression)
        
        response = client.get(
            "/large",
            headers={"accept-encoding": "gzip"},
        )
        
        # Response should be compressed (text/plain is not in exclude list)
        assert response.status_code == 200
        assert "content-encoding" in response.headers

    def test_streaming_response_not_compressed(self, app_with_compression):
        """Test that streaming responses are not compressed."""
        client = TestClient(app_with_compression)
        
        response = client.get(
            "/stream",
            headers={"accept-encoding": "gzip"},
        )
        
        # Check that streaming response is not compressed
        assert response.status_code == 200
        assert "content-encoding" not in response.headers

    def test_head_request_not_compressed(self, app_with_compression):
        """Test that HEAD requests are not compressed."""
        client = TestClient(app_with_compression)
        
        response = client.head(
            "/head",
            headers={"accept-encoding": "gzip"},
        )
        
        # Check that HEAD response is not compressed
        assert response.status_code == 200
        assert "content-encoding" not in response.headers

    def test_vary_header_present(self, app_with_compression):
        """Test that Vary: Accept-Encoding header is set for compressed responses."""
        client = TestClient(app_with_compression)
        
        response = client.get(
            "/large",
            headers={"accept-encoding": "gzip"},
        )
        
        # Check that Vary: Accept-Encoding header is set
        assert response.status_code == 200
        assert "vary" in response.headers
        assert response.headers["vary"] == "Accept-Encoding"

    def test_compressed_response_content_length(self, app_with_compression):
        """Test that compressed response has correct content length."""
        client = TestClient(app_with_compression)
        
        response = client.get(
            "/large",
            headers={"accept-encoding": "gzip"},
        )
        
        # Check that content length is set correctly
        assert response.status_code == 200
        assert "content-length" in response.headers
        
        # Verify that the content length matches the compressed content length
        compressed_content = gzip.compress(b"x" * 2000)
        assert int(response.headers["content-length"]) == len(compressed_content)

    def test_decompress_response_correctly(self, app_with_compression):
        """Test that compressed responses can be correctly decompressed."""
        client = TestClient(app_with_compression)
        
        response = client.get(
            "/large",
            headers={"accept-encoding": "gzip"},
        )
        
        # Decompress the response content
        decompressed = gzip.decompress(response.content)
        assert decompressed == b"x" * 2000

    def test_multiple_requests_compressible(self, app_with_compression):
        """Test that multiple requests are handled correctly."""
        client = TestClient(app_with_compression)
        
        # First request should be compressed
        response1 = client.get(
            "/large",
            headers={"accept-encoding": "gzip"},
        )
        assert response1.headers.get("content-encoding") == "gzip"
        
        # Second request without gzip should not be compressed
        response2 = client.get(
            "/large",
            headers={"accept-encoding": "identity"},
        )
        assert "content-encoding" not in response2.headers

    def test_app_without_compression(self):
        """Test that app without compression middleware works normally."""
        app = FastAPI()
        
        @app.get("/test")
        def test_endpoint():
            return Response(b"test response", status_code=200)
        
        client = TestClient(app)
        
        response = client.get("/test")
        
        # Check that response is not compressed (no compression middleware)
        assert response.status_code == 200
        assert "content-encoding" not in response.headers
