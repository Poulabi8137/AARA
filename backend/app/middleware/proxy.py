from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import get_settings


class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to handle X-Forwarded-For and X-Forwarded-Proto headers for HTTPS behind reverse proxy."""

    async def dispatch(self, request: Request, call_next):
        # Set forwarded protocol to determine if request is HTTPS
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
        if forwarded_proto.lower() == "https":
            request.scope["scheme"] = "https"

        # Set forwarded host for host validation
        forwarded_host = request.headers.get("X-Forwarded-Host")
        if forwarded_host:
            request.scope["server"] = (
                forwarded_host,
                443 if forwarded_proto == "https" else 80,
            )

        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response


class TrustedHostMiddleware(BaseHTTPMiddleware):
    """Middleware to validate trusted hosts for HTTPS security."""

    def __init__(self, app, trusted_hosts: list[str]):
        super().__init__(app)
        self.trusted_hosts = set(trusted_hosts)

    async def dispatch(self, request: Request, call_next):
        host = request.headers.get("host") or request.url.hostname

        # In production, validate against trusted hosts
        if host and self.trusted_hosts:
            # Extract hostname without port
            hostname = host.split(":")[0]
            if hostname not in self.trusted_hosts:
                return Response(
                    status_code=403,
                    content={"detail": "Invalid host header"},
                    media_type="application/json",
                )

        return await call_next(request)


def setup_proxy_middleware(app):
    """Setup proxy headers and trusted host middleware."""
    settings = get_settings()

    # Add proxy headers middleware for reverse proxy support
    app.add_middleware(ProxyHeadersMiddleware)

    # Add trusted host middleware for HTTPS security
    trusted_hosts = getattr(settings, "trusted_hosts", None)
    if trusted_hosts:
        app.add_middleware(TrustedHostMiddleware, trusted_hosts=trusted_hosts)


# Legacy proxy middleware for backward compatibility
class LegacyProxyMiddleware(BaseHTTPMiddleware):
    """Legacy proxy middleware for backward compatibility."""

    async def dispatch(self, request: Request, call_next):
        original_scheme = request.scope.get("scheme", "http")

        response = await call_next(request)

        response.headers["X-Original-Scheme"] = original_scheme
        return response
