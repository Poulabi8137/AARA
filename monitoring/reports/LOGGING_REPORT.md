# Logging Report

## Overview

This report documents the structured logging implementation for the AARA backend application. Logging is powered by [structlog](https://www.structlog.org/).

---

## Configuration

**Library:** structlog >= 24.4.0
**Configuration File:** `app/observability/logging.py`

### Log Levels

| Level | Default | Description |
|-------|---------|-------------|
| DEBUG | Development | Detailed debugging information |
| INFO | Production | General operational information |
| WARNING | Both | Unexpected but handled events |
| ERROR | Both | Error conditions that require attention |
| CRITICAL | Both | Critical failures requiring immediate action |

### Environment-Specific Configuration

#### Development Mode
- Console output with colored formatting
- Human-readable timestamps (`%Y-%m-%d %H:%M:%S`)
- Stack traces included
- WARNING level includes exception info

#### Production Mode
- JSON output format (machine-parseable)
- ISO 8601 UTC timestamps
- Structured fields for log aggregation
- Correlation IDs included in all log events

---

## Structured Log Fields

Every structured log event includes the following fields:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `event` | string | Log message | "request_processed" |
| `level` | string | Log level | "info" |
| `logger` | string | Logger name | "aara.api" |
| `timestamp` | string | ISO 8601 timestamp | "2026-06-23T12:00:00Z" |
| `correlation_id` | string | Request correlation ID | "req-a1b2c3d4" |
| `service` | string | Service name | "aara-backend" |
| `version` | string | Application version | "0.3.0" |

---

## Correlation IDs

### Propagation Flow

1. **Request enters** → `RequestIDMiddleware` generates UUID and binds to `structlog.contextvars`
2. **Logging occurs** → `inject_correlation_id` processor reads from contextvars and adds to event
3. **Response leaves** → `X-Request-ID` header set on response
4. **Context cleared** → `finally` block clears structlog contextvars

### Implementation Details

- **Middleware:** `app/core/middleware.py` - `RequestIDMiddleware` class
- **Logging Processor:** `app/observability/logging.py` - `inject_correlation_id` function
- **Header:** `X-Request-ID` set on every response

---

## Logger Usage

```python
from app.observability.logging import get_logger

logger = get_logger("aara.service_name")

# Basic logging
logger.info("service_started")
logger.error("operation_failed", operation="research", error=str(exc))

# With structured context
logger.warning("rate_limit_exceeded",
    client_ip=request.client.host,
    endpoint=request.url.path,
    retry_after=60,
)
```

---

## Health Endpoints Logging

The following health endpoints generate structured logs:

| Endpoint | Method | Log Events |
|----------|--------|------------|
| `/health` | GET | `health_check`, `database_status`, `cache_status` |
| `/health/live` | GET | `liveness_check` |
| `/health/ready` | GET | `readiness_check`, `database_status` |

---

## Log Rotation & Retention

| Environment | Retention | Rotation |
|-------------|-----------|----------|
| Development | 7 days | N/A (stdout) |
| Staging | 30 days | Daily |
| Production | 90 days | Daily + Compressed |
