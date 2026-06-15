# Structured Logging Architecture

## Overview

AARA uses structured JSON logging throughout the backend. Every log entry is a JSON object parsable by log aggregation tools (ELK, Grafana Loki, Datadog, etc.).

## Log Format

```json
{
  "timestamp": "2026-06-15T12:00:00.000Z",
  "level": "INFO",
  "logger": "middleware",
  "message": "request completed",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "method": "GET",
  "endpoint": "/api/projects",
  "status_code": 200,
  "execution_time_ms": 45.23,
  "user_id": "user-uuid-here",
  "context": {
    "extra_field": "value"
  }
}
```

## Key Fields

| Field | Description | Always Present |
|-------|-------------|----------------|
| `timestamp` | ISO 8601 UTC | Yes |
| `level` | DEBUG/INFO/WARNING/ERROR | Yes |
| `logger` | Module name | Yes |
| `message` | Human-readable description | Yes |
| `request_id` | Unique per-request UUID | Request-scoped |
| `correlation_id` | End-to-end trace ID (propagated from client) | Request-scoped |
| `user_id` | Authenticated user ID | When authenticated |
| `endpoint` | URL path | Request-scoped |
| `status_code` | HTTP response code | Request-scoped |
| `execution_time_ms` | Handler execution time | Request-scoped |
| `exception` | Stack trace | On error |

## Correlation ID Propagation

1. **Client sends** `X-Correlation-ID` header (optional)
2. **Middleware** at `middleware/setup.py:RequestLoggingMiddleware`:
   - Reads `X-Correlation-ID` from incoming request headers
   - Falls back to `request_id` if absent
   - Sets `request.state.correlation_id`
   - Adds `X-Correlation-ID` to response headers
3. **Downstream services** (LLM calls, DB queries) can propagate via their respective clients

## Log Levels

| Level | Usage |
|-------|-------|
| `DEBUG` | Development details, not emitted in production |
| `INFO` | Normal operations — request lifecycle, startup/shutdown |
| `WARNING` | Degraded functionality — Redis unavailable, fallback used |
| `ERROR` | Recoverable errors — failed DB query, auth failure |

## Middleware Integration

The `RequestLoggingMiddleware` in `middleware/setup.py`:
- Generates `request_id` (UUID v4)
- Captures `correlation_id` from headers
- Measures execution time
- Attaches `user_id` from JWT auth
- Logs structured JSON on every request completion
- Sets response headers `X-Request-ID` and `X-Correlation-ID`

## Usage in Application Code

```python
from app.core.logging import get_logger

logger = get_logger("my.module")
logger.info("processing item", extra={
    "item_id": item_id,
    "request_id": request.state.request_id,
})
```

## Log Aggregation

Logs are emitted to stdout in JSON format, suitable for:
- **Docker**: `docker logs` natively shows JSON
- **Grafana Loki**: Structured JSON parsed automatically
- **ELK Stack**: Filebeat → Logstash → Elasticsearch
- **CloudWatch**: Structured JSON parsed automatically
