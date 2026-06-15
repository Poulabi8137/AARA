from __future__ import annotations


from pydantic import BaseModel


class ServiceStatus(BaseModel):
    status: str  # "healthy" | "unhealthy" | "degraded"
    latency_ms: float = 0.0
    error: str | None = None


class HealthResponse(BaseModel):
    status: str  # "healthy" | "degraded" | "unhealthy"
    version: str = "0.1.0"
    timestamp: str = ""
    uptime_seconds: float = 0.0
    services: dict[str, ServiceStatus] = {}


class ReadinessResponse(BaseModel):
    status: str  # "ready" | "not_ready"
    checks: dict[str, ServiceStatus]


class LivenessResponse(BaseModel):
    status: str  # "alive"
    timestamp: str = ""
